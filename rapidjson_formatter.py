from __future__ import print_function
import lldb
import lldb.formatters.Logger
import sys
import traceback

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


kNullType = 0
kFalseType = 1
kTrueType = 2
kObjectType = 3
kArrayType = 4
kStringType = 5
kNumberType = 6

kBoolFlag = 0x0008
kNumberFlag = 0x0010
kIntFlag = 0x0020
kUintFlag = 0x0040
kInt64Flag = 0x0080
kUint64Flag = 0x0100
kDoubleFlag = 0x0200
kStringFlag = 0x0400
kCopyFlag = 0x0800
kInlineStrFlag = 0x1000
kObjectFlag = kObjectType
kArrayFlag = kArrayType

kNullFlag = kNullType
kTrueFlag = kTrueType | kBoolFlag
kFalseFlag = kFalseType | kBoolFlag
kNumberIntFlag = kNumberType | kNumberFlag | kIntFlag | kInt64Flag
kNumberUintFlag = kNumberType | kNumberFlag | kUintFlag | kUint64Flag | kInt64Flag
kNumberInt64Flag = kNumberType | kNumberFlag | kInt64Flag
kNumberUint64Flag = kNumberType | kNumberFlag | kUint64Flag
kNumberDoubleFlag = kNumberType | kNumberFlag | kDoubleFlag
kNumberAnyFlag = kNumberType | kNumberFlag | kIntFlag | kInt64Flag | kUintFlag | kUint64Flag | kDoubleFlag
kConstStringFlag = kStringType | kStringFlag
kCopyStringFlag = kStringType | kStringFlag | kCopyFlag
kShortStringFlag = kStringType | kStringFlag | kCopyFlag | kInlineStrFlag


def get_string_from_array(array):
    size = array.GetNumChildren()
    res = ""
    i = 0
    while i < size:
        v = array.GetChildAtIndex(i, lldb.eNoDynamicValues, True).GetValueAsUnsigned()
        if v == 0:
            break
        res += chr(v)
        i += 1

    return res


def get_string_from_memory(starting_address):
    res = ""
    address = starting_address

    error_ref = lldb.SBError()
    process = lldb.debugger.GetSelectedTarget().GetProcess()
    chunk_size = 1024
    while True:
        memory = process.ReadMemory(address, chunk_size, error_ref)
        if not error_ref.Success():
            return ""
        b = bytearray(memory)
        i = 0
        while i < chunk_size:
            v = b[i]
            if v == 0:
                return res
            res += chr(v)
            i += 1
        address += chunk_size


def rapidjson_SummaryProvider(valobj, dict):
    eprint("summary_provider")
    synth = rapidjson_SynthProvider(valobj, dict)
    synth.update()
    return synth.get_summary()


class rapidjson_SynthProvider:
    def __init__(self, valobj, dict):
        self.valobj = valobj
        self.data = None
        self.flags = None

    def num_children(self):
        try:
            res = self._get_num_children()
            eprint("num_children %s" % res)
            return res
        except:
            traceback.print_exc()
            return 0

    def _get_num_children(self):
        if self.flags == kArrayFlag:
            data = self._get_data_object("a")
            return data.GetChildMemberWithName("size").GetValueAsUnsigned()
        if self.flags == kObjectFlag:
            data = self._get_data_object("o")
            return data.GetChildMemberWithName("size").GetValueAsUnsigned()
        return 0

    def get_child_index(self, name):
        eprint("get_child_index: %s" % name)
        try:
            return -1
        except:
            traceback.print_exc()
            return -1

    def get_child_at_index(self, index):
        eprint("get_child_at_index: %s" % index)

        try:
            res = self._get_child_at_index(index)
            eprint("res %s: %s" % (index, res))
            return res
        except:
            traceback.print_exc()
            return None

    def _get_child_at_index(self, index):
        eprint("index: %s" % index)

        if self.flags == kArrayFlag: return self._get_array_child(index)

        return None

    def _get_array_child(self, index):
        arr = self._get_data_object("a")
        start = arr.GetChildMemberWithName("elements")
        type = start.GetType().GetPointeeType()
        offset = index * type.GetByteSize()
        address = self._get_valid_address(start) + offset
        return start.CreateValueFromAddress('[' + str(index) + ']', address, type)

    def update(self):
        eprint("update")
        self.data = self.valobj.GetChildMemberWithName("data_")
        self.flags = self._get_flags()
        eprint("flags %s" % self.flags)

    def has_children(self):
        res = self.flags == kArrayFlag or self.flags == kObjectFlag
        eprint("has_children %s" % res)
        return res

    def get_summary(self):
        eprint("get_summary")
        try:
            if self.flags == kNullFlag:      return "null"
            if self.flags == kFalseFlag:     return "false"
            if self.flags == kTrueFlag:      return "true"
            if self.flags == kArrayFlag:     return "Array, size=%s" % self.num_children()
            if self.flags == kObjectFlag:    return "Object, size=%s" % self.num_children()
            if self._is_set(kInlineStrFlag): return self._get_inline_string()
            if self._is_set(kStringFlag):    return self._get_string()
            if self._is_set(kDoubleFlag):    return self._get_number_object("d").GetValue()
            if self._is_set(kUint64Flag):    return self._get_number_object("u64").GetValue()
            if self._is_set(kInt64Flag):     return self._get_number_object("i64").GetValue()
            if self._is_set(kUintFlag):      return self._get_number_object("u").GetChildMemberWithName("u").GetValue()
            if self._is_set(kIntFlag):       return self._get_number_object("i").GetChildMemberWithName("i").GetValue()
            return None
        except:
            return None

    def _is_set(self, flag):
        return (self.flags & flag) != 0

    def _get_data_object(self, type):
        return self.data.GetChildMemberWithName(type)

    def _get_number_object(self, type):
        return self._get_data_object("n").GetChildMemberWithName(type)

    def _get_flags(self):
        f = self.data.GetChildMemberWithName("f")
        flags = f.GetChildMemberWithName("flags")
        return flags.GetValueAsUnsigned()

    def _get_inline_string(self):
        ss = self._get_data_object("ss")
        str = ss.GetChildMemberWithName("str")
        return '"%s"' % get_string_from_array(str)

    def _get_string(self):
        s = self._get_data_object("s")
        str = s.GetChildMemberWithName("str")
        address = self._get_valid_address(str)

        return '"%s"' % get_string_from_memory(address)

    def _get_valid_address(self, obj):
        return int(obj.GetValue(), 16) & 0x0000FFFFFFFFFFFF


def __lldb_init_module(debugger, dict):
    debugger.HandleCommand(
         'type synthetic add -l rapidjson_formatter.rapidjson_SynthProvider -x "^rapidjson::GenericValue<.+>$" -w rapidjson')
    # debugger.HandleCommand(
    #     'type summary add -F rapidjson_formatter.rapidjson_SummaryProvider -e -x "^rapidjson::GenericValue<.+>$" -w rapidjson')
    debugger.HandleCommand("type category enable rapidjson")


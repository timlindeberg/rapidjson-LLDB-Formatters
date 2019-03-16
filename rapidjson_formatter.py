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
    synth = rapidjson_SynthProvider(valobj, dict)
    synth.update()
    summary = synth.get_summary()
    return summary


class rapidjson_SynthProvider:
    def __init__(self, valobj, dict):
        self.valobj = valobj

        self.data = None
        self.flags = None
        self.type = self.valobj.GetType()

    def num_children(self):
        eprint("num_children %s" % self.valobj.GetName())
        try:
            res = self._get_num_children()
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
        eprint("get_child_index(%s) %s" % (name, self.valobj.GetName()))
        try:
            return -1
        except:
            traceback.print_exc()
            return -1

    def get_child_at_index(self, index):
        if index < 0:
            return None
        if index >= self.num_children():
            return None

        try:
            if self.flags == kArrayFlag: return self._get_array_child(index)
            if self.flags == kObjectFlag: return self._get_object_child(index)
            return None
        except:
            traceback.print_exc()
            return None

    def _get_array_child(self, index):
        arr = self._get_data_object("a")
        start = arr.GetChildMemberWithName("elements")
        offset = index * self.type.GetByteSize()
        address = self._get_valid_address(start) + offset
        return self.valobj.CreateValueFromAddress('[' + str(index) + ']', address, self.type)

    def _get_object_child(self, index):
        address = self._get_member_address(index)
        masked_address = str(self._mask_address(address))
        name = self._get_object_name(masked_address, index)

        # We need to create a value form address, otherwise we won't
        # be able to read the data_ object of the created child
        obj_child = self.valobj.CreateValueFromExpression(name + "addr", "&reinterpret_cast<rapidjson::Value::Member*>(" + masked_address + ")->value")
        child_address = int(obj_child.GetValue(), 16)
        return self.valobj.CreateValueFromAddress(name, child_address, self.type)

    def _get_object_name(self, address, index):
        data_value = self.valobj.CreateValueFromExpression("name", "reinterpret_cast<rapidjson::Value::Member*>(" + address + ")->name->data_")
        flags = self._get_flags(data_value)
        is_inline = flags & kInlineStrFlag != 0
        member_name = self._get_inline_string(data_value) if is_inline else self._get_string(data_value)
        return '[%s] %s' % (index, member_name)

    def _get_member_address(self, index):
        obj = self._get_data_object("o")
        start = obj.GetChildMemberWithName("members")

        member_type = start.GetType().GetPointeeType()
        offset = index * member_type.GetByteSize()
        return self._get_valid_address(start) + offset

    def update(self):
        eprint("update %s" % self.valobj.GetName())

        # We read the address of the object and use that in CreateValueFromExpression
        # to fetch the data_ object. This seems to be the only way to access data_
        # once we've attached a synthetic children provider to the same type
        address = self.valobj.GetAddress().GetOffset()
        self.data = self.valobj.CreateValueFromExpression("data", "reinterpret_cast<rapidjson::Value*>(" + str(address) + ")->data_")
        self.flags = self._get_flags(self.data)

    def has_children(self):
        return self.flags == kArrayFlag or self.flags == kObjectFlag

    def get_summary(self):
        eprint("get_summary %s" % self.valobj.GetName())

        try:
            if self.flags == kNullFlag:      return "null"
            if self.flags == kFalseFlag:     return "false"
            if self.flags == kTrueFlag:      return "true"
            if self.flags == kArrayFlag:     return "<Array> size=%s" % self.num_children()
            if self.flags == kObjectFlag:    return "<Object> size=%s" % self.num_children()
            if self._is_set(kInlineStrFlag): return self._get_inline_string(self.data)
            if self._is_set(kStringFlag):    return self._get_string(self.data)
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

    def _get_flags(self, data_value):
        f = data_value.GetChildMemberWithName("f")
        flags = f.GetChildMemberWithName("flags")
        return flags.GetValueAsUnsigned()

    def _get_inline_string(self, data_value):
        ss = data_value.GetChildMemberWithName("ss")
        str = ss.GetChildMemberWithName("str")

        return '"%s"' % get_string_from_array(str)

    def _get_string(self, data_value):
        s = data_value.GetChildMemberWithName("s")
        str = s.GetChildMemberWithName("str")
        address = self._get_valid_address(str)

        return '"%s"' % get_string_from_memory(address)

    def _get_pointer_adress(self, pointer_value):
        return int(pointer_value.GetValue(), 16)

    def _get_valid_address(self, obj):
        return self._mask_address(self._get_pointer_adress(obj))

    def _mask_address(self, address):
        return address & 0x0000FFFFFFFFFFFF


def __lldb_init_module(debugger, dict):
    debugger.HandleCommand(
        'type summary add -F rapidjson_formatter.rapidjson_SummaryProvider -e -x "^rapidjson::GenericValue<.+>$" -w rapidjson')
    debugger.HandleCommand(
         'type synthetic add -l rapidjson_formatter.rapidjson_SynthProvider -x "^rapidjson::GenericValue<.+>$" -w rapidjson_synth')
    debugger.HandleCommand(
        'type synthetic add -l rapidjson_formatter.rapidjson_SynthProvider -x "^rapidjson::Document$" -w rapidjson_synth')
    debugger.HandleCommand("type category enable rapidjson")
    debugger.HandleCommand("type category enable rapidjson_synth")


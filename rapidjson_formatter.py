from __future__ import print_function
import lldb
import lldb.formatters.Logger
import traceback

def eprint(*args, **kwargs):
    import sys
    print(*args, file=sys.stderr, **kwargs)


def __lldb_init_module(debugger, dict):
    debugger.HandleCommand(
        'type summary add -F rapidjson_formatter.SummaryProvider -e -x "^rapidjson::GenericValue<.+>$" -w rapidjson')
    debugger.HandleCommand(
        'type synthetic add -l rapidjson_formatter.SynthProvider -x "^rapidjson::GenericValue<.+>$" -w rapidjson')
    debugger.HandleCommand(
        'type synthetic add -l rapidjson_formatter.SynthProvider -x "^rapidjson::Document$" -w rapidjson')
    debugger.HandleCommand("type category enable rapidjson")


def SummaryProvider(valobj, dict):
    synth = SynthProvider(valobj, dict)
    synth.update()
    return synth.get_summary()

class SynthProvider:
    def __init__(self, valobj, dict):
        self.valobj = valobj
        self.data = None
        self.flags = None
        self.type = self.valobj.GetType()
        self._num_children = 0

    def num_children(self):
        return self._num_children

    def get_child_index(self, name):
        try:
            return int(name[1:name.rfind("]")])
        except:
            traceback.print_exc()
            return -1

    def get_child_at_index(self, index):
        try:
            if index < 0:
                return None
            if index >= self._num_children:
                return None

            if self.flags == kArrayFlag:  return self._get_array_child(index)
            if self.flags == kObjectFlag: return self._get_object_child(index)
            return None
        except:
            traceback.print_exc()
            return None

    def update(self):
        self.data = self._get_data_value()
        self.flags = get_flags(self.data)
        self._num_children = self._get_num_children()
        self.type = self._get_json_type()

    def has_children(self):
        return self._num_children > 0

    def get_summary(self):
        flags = self.flags

        def get_number_object(type):
            return self._get_object_on_data("n").GetChildMemberWithName(type)

        def is_set(flag):
            return is_flag_set(self.flags, flag)

        try:
            if flags == kNullFlag:     return "null"
            if flags == kFalseFlag:    return "false"
            if flags == kTrueFlag:     return "true"
            if flags == kArrayFlag:    return "<Array> size=%s" % self._num_children
            if flags == kObjectFlag:   return "<Object> size=%s" % self._num_children
            if is_set(kStringFlag):    return get_string(flags, self.data)
            if is_set(kDoubleFlag):    return get_number_object("d").GetValue()
            if is_set(kUint64Flag):    return get_number_object("u64").GetValue()
            if is_set(kInt64Flag):     return get_number_object("i64").GetValue()
            if is_set(kUintFlag):      return get_number_object("u").GetChildMemberWithName("u").GetValue()
            if is_set(kIntFlag):       return get_number_object("i").GetChildMemberWithName("i").GetValue()
            return None
        except:
            traceback.print_exc()
            return None

    def _get_data_value(self):
        # We read the address of the object and use that in CreateValueFromExpression
        # to fetch the data_ object. This seems to be the only way to access data_
        # once we've attached a synthetic children provider for this type
        address = self.valobj.GetAddress().GetOffset()
        expr = "reinterpret_cast<rapidjson::Value*>(%s)->data_" % address
        return self.valobj.CreateValueFromExpression("data", expr)

    def _get_num_children(self):
        def get_type():
            if self.flags == kArrayFlag:    return "a"
            elif self.flags == kObjectFlag: return "o"
            else:                           return ""
        try:
            return self._get_object_on_data(get_type()).GetChildMemberWithName("size").GetValueAsUnsigned()
        except:
            traceback.print_exc()
            return 0

    def _get_array_child(self, index):
        arr = self._get_object_on_data("a")
        start = arr.GetChildMemberWithName("elements")
        offset = index * self.type.GetByteSize()
        address = get_valid_address(start) + offset
        return self.valobj.CreateValueFromAddress('[' + str(index) + ']', address, self.type)

    def _get_object_child(self, index):
        address = self._get_member_address(index)
        masked_address = str(mask_address(address))
        name = self._get_object_name(masked_address, index)

        # We need to create a value form address, otherwise we won't
        # be able to read the data_ object of the created child.
        expr = "&reinterpret_cast<rapidjson::Value::Member*>(%s)->value" % masked_address
        obj_child = self.valobj.CreateValueFromExpression(name + "addr", expr)
        return self.valobj.CreateValueFromAddress(name, get_pointer_adress(obj_child), self.type)

    def _get_object_name(self, address, index):
        expr = "reinterpret_cast<rapidjson::Value::Member*>(%s)->name->data_" % address
        data_value = self.valobj.CreateValueFromExpression("name", expr)
        flags = get_flags(data_value)
        member_name = get_string(flags, data_value)
        return member_name

    def _get_member_address(self, index):
        obj = self._get_object_on_data("o")
        start = obj.GetChildMemberWithName("members")

        member_type = start.GetType().GetPointeeType()
        offset = index * member_type.GetByteSize()
        return get_valid_address(start) + offset

    def _get_object_on_data(self, type):
        return self.data.GetChildMemberWithName(type)

    def _get_json_type(self):
        type = self.valobj.GetType().GetCanonicalType()
        if "GenericDocument" in type.GetName():
            type = type.GetDirectBaseClassAtIndex(0).GetType()
        if type.IsPointerType():
            type = type.GetPointeeType()
        if type.IsReferenceType():
            type = type.GetDereferencedType()
        return type


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


def get_string(flags, data_value):
    if is_flag_set(flags, kInlineStrFlag):
        return get_inline_string(data_value)

    s = data_value.GetChildMemberWithName("s")
    str = s.GetChildMemberWithName("str")
    address = get_valid_address(str)

    return '"%s"' % get_string_from_memory(address)


def get_inline_string(data_value):
    ss = data_value.GetChildMemberWithName("ss")
    str = ss.GetChildMemberWithName("str")

    return '"%s"' % get_string_from_array(str)


def is_flag_set(flags, flag):
    return (flags & flag) != 0


def get_flags(data_value):
    f = data_value.GetChildMemberWithName("f")
    flags = f.GetChildMemberWithName("flags")
    return flags.GetValueAsUnsigned()


def mask_address(address):
    return address & 0x0000FFFFFFFFFFFF


def get_pointer_adress(pointer_value):
    return int(pointer_value.GetValue(), 16)


def get_valid_address(obj):
    return mask_address(get_pointer_adress(obj))


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

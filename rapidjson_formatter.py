import lldb
import lldb.formatters.Logger
import struct


def __lldb_init_module(debugger, dict):
    # GenericValue
    debugger.HandleCommand(
        'type summary add -F rapidjson_formatter.GenericValue_SummaryProvider -e -x "^rapidjson::GenericValue<.+>$" -w rapidjson')
    debugger.HandleCommand(
        'type synthetic add -l rapidjson_formatter.GenericValue_SynthProvider -x "^rapidjson::GenericValue<.+>$" -w rapidjson')

    # GenericDocument
    debugger.HandleCommand(
        'type synthetic add -l rapidjson_formatter.GenericValue_SynthProvider -x "^rapidjson::GenericDocument<.+>$" -w rapidjson')
    debugger.HandleCommand(
        'type summary add -F rapidjson_formatter.GenericValue_SummaryProvider -e -x "^rapidjson::GenericDocument<.+>$" -w rapidjson')

    # GenericArray
    debugger.HandleCommand(
        'type summary add -F rapidjson_formatter.GenericArrayAndObject_SummaryProvider -e -x "^rapidjson::GenericArray<.+>$" -w rapidjson')
    debugger.HandleCommand(
        'type synthetic add -l rapidjson_formatter.GenericArrayAndObject_SynthProvider -x "^rapidjson::GenericArray<.+>$" -w rapidjson')

    # GenericObject
    debugger.HandleCommand(
        'type summary add -F rapidjson_formatter.GenericArrayAndObject_SummaryProvider -e -x "^rapidjson::GenericObject<.+>$" -w rapidjson')
    debugger.HandleCommand(
        'type synthetic add -l rapidjson_formatter.GenericArrayAndObject_SynthProvider -x "^rapidjson::GenericObject<.+>$" -w rapidjson')

    debugger.HandleCommand("type category enable rapidjson")


def GenericValue_SummaryProvider(valobj, dict):
    synth = GenericValue_SynthProvider(valobj, dict)
    synth.update()
    return synth.get_summary()


class GenericValue_SynthProvider:
    def __init__(self, valobj, dict):
        valobj.SetPreferSyntheticValue(False)
        self.valobj = valobj
        self.dict = dict
        self.data = None
        self.flags = None
        self.type = None
        self.number_of_children = 0

    def update(self):
        self.data = self.valobj.GetChildMemberWithName("data_")
        self.flags = self._get_flags()
        self.type = self._find_type()
        self.number_of_children = self._get_num_children()

    def num_children(self):
        return self.number_of_children

    def get_child_index(self, name):
        if not name or name[0] != "[":
            return -1
        return int(name[1:name.rfind("]")])

    def get_child_at_index(self, index):
        if self.flags == kArrayFlag:         return self._get_array(index)
        if self.flags == kObjectFlag:        return self._get_object(index)
        return None

    def has_children(self):
        return self.number_of_children > 0

    def get_summary(self):
        flags = self.flags

        def get_number_object(type):
            return self._get_data("n").GetChildMemberWithName(type)

        if flags == kNullFlag:        return "null"
        if flags == kFalseFlag:       return "false"
        if flags == kTrueFlag:        return "true"
        if flags == kArrayFlag:       return "<Array> size=%s" % self.number_of_children
        if flags == kObjectFlag:      return "<Object> size=%s" % self.number_of_children
        if self._is_set(kStringFlag): return self._get_string()
        if self._is_set(kDoubleFlag): return get_number_object("d").GetValue()
        if self._is_set(kUint64Flag): return get_number_object("u64").GetValue()
        if self._is_set(kInt64Flag):  return get_number_object("i64").GetValue()
        if self._is_set(kUintFlag):   return get_number_object("u").GetChildMemberWithName("u").GetValue()
        if self._is_set(kIntFlag):    return get_number_object("i").GetChildMemberWithName("i").GetValue()
        return None

    def _get_flags(self):
        flags = self._get_data("f").GetChildMemberWithName("flags")
        return flags.GetValueAsUnsigned()

    def _is_set(self, flag):
        return (self.flags & flag) != 0

    def _get_data(self, name):
        return self.data.GetChildMemberWithName(name)

    def _find_type(self):
        type = self.valobj.GetType().GetCanonicalType()
        if "GenericDocument" in type.GetName():
            type = type.GetDirectBaseClassAtIndex(0).GetType()

        if type.IsPointerType():
            type = type.GetPointeeType()
        if type.IsReferenceType():
            type = type.GetDereferencedType()
        return type

    def _get_num_children(self):
        if self.flags != kArrayFlag and self.flags != kObjectFlag:
            return 0

        obj = "a" if self.flags == kArrayFlag else "o"
        return self._get_data(obj).GetChildMemberWithName("size").GetValueAsUnsigned()

    def _get_array(self, index):
        arr = self._get_data("a")
        start = arr.GetChildMemberWithName("elements")
        offset = index * self.type.GetByteSize()
        address = self._get_valid_address(start) + offset
        return self.valobj.CreateValueFromAddress('[' + str(index) + ']', address, self.type)

    def _get_object(self, index):
        member = self._get_member_value(index)
        name = self._get_name(member)
        data = member.GetChildMemberWithName("value").GetData()
        return self.valobj.CreateValueFromData(name, data, self.type)

    def _get_member_value(self, index):
        obj = self._get_data("o")
        members_pointer = obj.GetChildMemberWithName("members")
        member_type = members_pointer.GetType().GetPointeeType()
        offset = index * member_type.GetByteSize()
        address = self._get_valid_address(members_pointer) + offset
        return self.valobj.CreateValueFromAddress("members" + str(index), address, member_type)

    def _get_name(self, member_value):
        name_value = member_value.GetChildMemberWithName("name")
        name_synth = GenericValue_SynthProvider(name_value, self.dict)
        name_synth.update()
        return name_synth.get_summary()

    def _get_string(self):
        if self._is_set(kInlineStrFlag):
            return self._get_inline_string()

        str = self._get_data("s").GetChildMemberWithName("str")
        address = self._get_valid_address(str)

        return '"%s"' % self._get_string_from_memory(address)

    def _get_inline_string(self):
        str = self._get_data("ss").GetChildMemberWithName("str")
        return '"%s"' % self._get_string_from_array(str)

    def _get_valid_address(self, pointer_value):
        address = int(pointer_value.GetValue(), 16)
        is_64_bit_os = struct.calcsize("P") == 8
        return address & 0x0000FFFFFFFFFFFF if is_64_bit_os else address

    def _get_string_from_array(self, array):
        size = array.GetNumChildren()
        res = ""
        i = 0
        while i < size:
            v = array.GetChildAtIndex(i).GetValueAsUnsigned()
            if v == 0:
                break
            res += chr(v)
            i += 1

        return res

    def _get_string_from_memory(self, starting_address):
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


def GenericArrayAndObject_SummaryProvider(valobj, dict):
    synth = GenericArrayAndObject_SynthProvider(valobj, dict)
    synth.update()
    return synth.get_summary()


class GenericArrayAndObject_SynthProvider:
    def __init__(self, valobj, dict):
        valobj.SetPreferSyntheticValue(False)
        self.valobj = valobj
        self.dict = dict
        self.val_synth = None

    def update(self):
        val = self.valobj.GetChildMemberWithName("value_").Dereference()
        self.val_synth = GenericValue_SynthProvider(val, self.dict)
        self.val_synth.update()

    def num_children(self):
        return self.val_synth.num_children()

    def get_child_index(self, name):
        return self.val_synth.get_child_index(name)

    def get_child_at_index(self, index):
        return self.val_synth.get_child_at_index(index)

    def has_children(self):
        return self.val_synth.has_children()

    def get_summary(self):
        is_null = self.val_synth.flags == kNullFlag
        return "null" if is_null else "size=%s" % self.num_children()


# Taken directly from rapidjson/document.h
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

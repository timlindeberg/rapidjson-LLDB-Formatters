import lldb
import struct
import os


def __lldb_init_module(debugger, _dict):
    file_name = os.path.splitext(os.path.basename(__file__))[0]

    def add_providers(type, summary, synth):
        debugger.HandleCommand(
            'type summary add -F %s.%s -e -x "^rapidjson::%s<.+>$" -w rapidjson' % (file_name, summary, type))
        debugger.HandleCommand(
            'type synthetic add -l %s.%s -x "^rapidjson::%s<.+>$" -w rapidjson' % (file_name, synth, type))

    add_providers('GenericValue',    'GenericValue_SummaryProvider',   'GenericValue_SyntheticProvider')
    add_providers('GenericDocument', 'GenericValue_SummaryProvider',   'GenericValue_SyntheticProvider')
    add_providers('GenericArray',    'GenericWrapper_SummaryProvider', 'GenericWrapper_SyntheticProvider')
    add_providers('GenericObject',   'GenericWrapper_SummaryProvider', 'GenericWrapper_SyntheticProvider')

    debugger.HandleCommand('type category enable rapidjson')


def GenericValue_SummaryProvider(valobj, dict):
    synth = GenericValue_SyntheticProvider(valobj, dict)
    synth.update()
    return synth.get_summary()


class GenericValue_SyntheticProvider:
    def __init__(self, valobj, dict):
        valobj.SetPreferSyntheticValue(False)
        self.valobj = valobj
        self.dict = dict
        self.data = None
        self.flags = None
        self.number_of_children = 0

    def update(self):
        self.data = self.valobj.GetChildMemberWithName('data_')
        self.flags = self._get_flags()
        self.number_of_children = self._get_num_children()

    def num_children(self):
        return self.number_of_children

    def get_child_index(self, name):
        return int(name[1:name.rfind(']')]) if name and name[0] == '[' else -1

    def get_child_at_index(self, index):
        if self.flags == kArrayFlag:  return self._get_array(index)
        if self.flags == kObjectFlag: return self._get_object(index)
        return None

    def has_children(self):
        return self.number_of_children > 0

    def get_summary(self):
        flags = self.flags

        def get_number_object(name):
            return self._get_data('n').GetChildMemberWithName(name)

        if flags == kNullFlag:        return 'null'
        if flags == kFalseFlag:       return 'false'
        if flags == kTrueFlag:        return 'true'
        if flags == kArrayFlag:       return '<Array> size=%s'  % self.number_of_children
        if flags == kObjectFlag:      return '<Object> size=%s' % self.number_of_children
        if self._is_set(kStringFlag): return '"%s"'             % self._get_string()
        if self._is_set(kDoubleFlag): return '<Double> %s'      % get_number_object('d').GetValue()
        if self._is_set(kIntFlag):    return '<Int> %s'         % get_number_object('i').GetChildMemberWithName('i').GetValue()
        if self._is_set(kUintFlag):   return '<Uint> %s'        % get_number_object('u').GetChildMemberWithName('u').GetValue()
        if self._is_set(kUint64Flag): return '<Uint64> %s'      % get_number_object('u64').GetValue()
        if self._is_set(kInt64Flag):  return '<Int64> %s'       % get_number_object('i64').GetValue()
        return None

    def _get_flags(self):
        flags = self._get_data('f').GetChildMemberWithName('flags')
        return flags.GetValueAsUnsigned()

    def _is_set(self, flag):
        return (self.flags & flag) != 0

    def _get_data(self, name):
        return self.data.GetChildMemberWithName(name)

    def _get_num_children(self):
        if self.flags != kArrayFlag and self.flags != kObjectFlag:
            return 0

        name = 'a' if self.flags == kArrayFlag else 'o'
        return self._get_data(name).GetChildMemberWithName('size').GetValueAsUnsigned()

    def _get_array(self, index):
        array_data = self._get_data('a')
        elements = array_data.GetChildMemberWithName('elements')
        element_type = elements.GetType().GetPointeeType()
        offset = index * element_type.GetByteSize()
        address = self._get_address(elements) + offset
        return self.valobj.CreateValueFromAddress('[%s]' % index, address, element_type)

    def _get_object(self, index):
        member = self._get_member_value(index)
        name = self._get_name(member)
        value = member.GetChildMemberWithName('value')
        return member.CreateChildAtOffset(name, value.GetByteSize(), value.GetType())

    def _get_member_value(self, index):
        object_data = self._get_data('o')
        members_pointer = object_data.GetChildMemberWithName('members')
        member_type = members_pointer.GetType().GetPointeeType()
        offset = index * member_type.GetByteSize()
        address = self._get_address(members_pointer) + offset
        return self.valobj.CreateValueFromAddress('member%s' % index, address, member_type)

    def _get_name(self, member_value):
        name_value = member_value.GetChildMemberWithName('name')
        name_synth = GenericValue_SyntheticProvider(name_value, self.dict)
        name_synth.update()
        return name_synth.get_summary()

    def _get_string(self):
        if self._is_set(kInlineStrFlag):
            str_value = self._get_data('ss').GetChildMemberWithName('str')
            address = str_value.GetAddress().GetOffset()
            return self._read_string_from_memory(address, chunk_size=32)
        else:
            str_value = self._get_data('s').GetChildMemberWithName('str')
            address = self._get_address(str_value)
            return self._read_string_from_memory(address, chunk_size=1024)

    def _read_string_from_memory(self, starting_address, chunk_size):
        error_ref = lldb.SBError()
        process = lldb.debugger.GetSelectedTarget().GetProcess()

        chars = []
        address = starting_address
        while True:
            memory = process.ReadMemory(address, chunk_size, error_ref)
            if not error_ref.Success():
                return 'Could not read memory 0x%x' % address
            for c in memory:
                if c == '\0':
                    return ''.join(chars)
                chars.append(c)
            address += chunk_size

    def _get_address(self, pointer_value):
        address = int(pointer_value.GetValue(), 16)
        return address & 0x0000FFFFFFFFFFFF if IS_64_BIT_OS else address


def GenericWrapper_SummaryProvider(valobj, dict):
    synth = GenericWrapper_SyntheticProvider(valobj, dict)
    synth.update()
    return synth.get_summary()


class GenericWrapper_SyntheticProvider:
    def __init__(self, valobj, dict):
        valobj.SetPreferSyntheticValue(False)
        self.valobj = valobj
        self.dict = dict
        self.val_synth = None

    def update(self):
        val = self.valobj.GetChildMemberWithName('value_').Dereference()
        self.val_synth = GenericValue_SyntheticProvider(val, self.dict)
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
        return 'null' if is_null else 'size=%s' % self.num_children()


IS_64_BIT_OS = struct.calcsize('P') == 8

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

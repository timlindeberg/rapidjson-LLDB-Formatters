import lldb
import lldb.formatters.Logger

lldb.formatters.Logger._lldb_formatters_debug_level = 2
lldb.formatters.Logger._lldb_formatters_debug_filename = "/Users/tlin/lldboutput.txt"

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
kObjectFlag = kObjectType
kArrayFlag = kArrayType

logger = lldb.formatters.Logger.Logger()


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
    CHUNK_SIZE = 1024
    while True:
        memory = process.ReadMemory(address, CHUNK_SIZE, error_ref)
        if not error_ref.Success():
            return ""
        b = bytearray(memory)
        i = 0
        while i < CHUNK_SIZE:
            v = b[i]
            if v == 0:
                return res
            res += chr(v)
            i += 1
        address += CHUNK_SIZE


def value_SummaryProvider(valobj, dict):
    try:
        data = valobj.GetChildMemberWithName("data_")
        f = data.GetChildMemberWithName("f")
        flags = f.GetChildMemberWithName("flags").GetValueAsUnsigned()

        if flags == kNullFlag:  return "null"
        if flags == kFalseFlag: return "false"
        if flags == kTrueFlag:  return "true"

        if flags & kStringFlag != 0:
            if flags & kInlineStrFlag != 0:
                ss = data.GetChildMemberWithName("ss")
                str = ss.GetChildMemberWithName("str")
                return '"%s"' % get_string_from_array(str)
            else:
                s = data.GetChildMemberWithName("s")
                str = s.GetChildMemberWithName("str")
                adress = int(str.GetValue(), 16) & 0x0000FFFFFFFFFFFF
                return '"%s"' % get_string_from_memory(adress)

        n = data.GetChildMemberWithName("n")
        if flags & kDoubleFlag != 0: return n.GetChildMemberWithName("d").GetValue()
        if flags & kUint64Flag != 0: return n.GetChildMemberWithName("u64").GetValue()
        if flags & kInt64Flag != 0:  return n.GetChildMemberWithName("i64").GetValue()
        if flags & kUintFlag != 0:   return n.GetChildMemberWithName("u").GetChildMemberWithName("u").GetValue()
        if flags & kIntFlag != 0:    return n.GetChildMemberWithName("i").GetChildMemberWithName("i").GetValue()
        return None
    except:
        return None


class ValueFormatter:
    def __init__(self, valobj, dict):
        self.valobj = valobj

    def num_children(self):
        logger >> "num_children"
        return self.child_count

    def get_child_index(self, name):
        logger >> "get_child_index"
        logger >> name
        try:
            return int(name.lstrip('[').rstrip(']'))
        except:
            return -1

    def get_child_at_index(self, index):
        logger >> "get_child_at_index"
        logger >> index
        if index < 0:
            return None
        if index >= self.num_children():
            return None
        try:
            offset = index * self.data_size
            return self.start.CreateChildAtOffset(
                '[' + str(index) + ']', offset, self.data_type)
        except:
            return None

    def update(self):
        logger >> "update"
        self.type = self.valobj.GetType().GetDirectBaseClassAtIndex(0).GetType()

        logger >> "lol"
        logger >> self.type
        flags = self.get_flags()
        is_array = flags & kArrayFlag != 0
        is_object = flags & kObjectFlag != 0
        if is_array:
            data = self.get_data_object("a")
            self.child_count = data.GetChildMemberWithName("size").GetValueAsUnsigned()
            self.children_exist = True
        elif is_object:
            data = self.get_data_object("o")
            self.child_count = data.GetChildMemberWithName("size").GetValueAsUnsigned()
            self.children_exist = True
        else:
            self.child_count = 0
            self.children_exist = False

    def has_children(self):
        logger >> "has_children"
        try:
            return self.children_exist
        except:
            return False

    def get_data_object(self, type):
        data = self.valobj.GetChildMemberWithName("data_")
        return data.GetChildMemberWithName(type)

    def get_flags(self):
        data = self.valobj.GetChildMemberWithName("data_")
        f = data.GetChildMemberWithName("f")
        return f.GetChildMemberWithName("flags").GetValueAsUnsigned()

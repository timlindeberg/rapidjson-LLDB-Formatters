#include <iostream>
#include "rapidjson/document.h"

typedef unsigned int uint32_t;

enum MaskingOperator {
    eMaskingOperatorDefault = 0,
    eMaskingOperatorAnd = 1,
    eMaskingOperatorOr = 2,
    eMaskingOperatorXor = 3,
    eMaskingOperatorNand = 4,
    eMaskingOperatorNor = 5
};

struct A {};

class MaskedData {
private:
    uint32_t value;
    uint32_t mask;
    MaskingOperator oper;

public:
    MaskedData(uint32_t V = 0, uint32_t M = 0,
               MaskingOperator P = eMaskingOperatorDefault)
            : value(V), mask(M), oper(P) {}

    uint32_t apply() {
        switch (oper) {
            case eMaskingOperatorAnd:
                return value & mask;
            case eMaskingOperatorOr:
                return value | mask;
            case eMaskingOperatorXor:
                return value ^ mask;
            case eMaskingOperatorNand:
                return ~(value & mask);
            case eMaskingOperatorNor:
                return ~(value | mask);
            case eMaskingOperatorDefault: // fall through
            default:
                return value;
        }
    }

    void setValue(uint32_t V) { value = V; }

    void setMask(uint32_t M) { mask = M; }

    void setOperator(MaskingOperator P) { oper = P; }
};


int main() {
    auto s = R"(
    {
        "int": 1,
        "float": 2.0,
        "true": true,
        "false": false,
        "null": null,
        "array": [1, 2, 3],
        "object": {
            "A": 1,
            "B": 2,
            "C": 3
        }
    }
    )";

    rapidjson::Document arr;
    arr.SetArray();
    arr.Parse(R"([1, 2, false, "ABC", 5])");



//    rapidjson::Value t;
//    t.SetBool(true);
//    rapidjson::Value f;
//    f.SetBool(false);
//    rapidjson::Value n;
//    n.SetNull();
//    rapidjson::Value i;
//    i.SetInt(1);
//    rapidjson::Value u;
//    u.SetUint(2);
//    rapidjson::Value i64;
//    i64.SetInt64(3);
//    rapidjson::Value u64;
//    u64.SetUint64(4);
//    rapidjson::Value fl;
//    fl.SetFloat(5.5);
//    rapidjson::Value d;
//    d.SetDouble(6.6);
//    rapidjson::Value ss;
//    ss.SetString("ABC", doc.GetAllocator());
//    rapidjson::Value s;
//    s.SetString(rapidjson::StringRef("ABC12345678910ABC12345678910ABC12345678910ABC12345678910ABC12345678910"));

    return 0;
}
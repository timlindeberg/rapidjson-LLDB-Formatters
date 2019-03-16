#include <iostream>
#include <vector>
#include "rapidjson/document.h"

int main() {
//    auto s = R"(
//    {
//        "int": 1,
//        "float": 2.0,
//        "true": true,
//        "false": false,
//        "null": null,
//        "array": [1, 2, 3],
//        "object": {
//            "A": 1,
//            "B": 2,
//            "C": 3
//        }
//    }
//    )";
//
//    arr.SetArray();
//    arr.Parse(R"([1, 2, false, "ABC", 5])");




    rapidjson::Value t;
    t.SetBool(true);
    rapidjson::Value f;
    f.SetBool(false);
    rapidjson::Value n;
    n.SetNull();
    rapidjson::Value i;
    i.SetInt(1);
    rapidjson::Value u;
    u.SetUint(2);
//    rapidjson::Value i64;
//    i64.SetInt64(3);
//    rapidjson::Value u64;
//    u64.SetUint64(4);
//    rapidjson::Value fl;
//    fl.SetFloat(5.5);
//    rapidjson::Value d;
//    d.SetDouble(6.6);
    rapidjson::Value ss;
    ss.SetString("ABC");
    rapidjson::Value s;
    s.SetString(rapidjson::StringRef("ABC12345678910ABC12345678910ABC12345678910ABC12345678910ABC12345678910"));

    rapidjson::Document doc;
    rapidjson::Value arr1;
    arr1.SetArray();
    arr1.PushBack(t, doc.GetAllocator());
    arr1.PushBack(f, doc.GetAllocator());
    arr1.PushBack(n, doc.GetAllocator());

    rapidjson::Value arr2;
    arr2.SetArray();
    arr2.PushBack(i, doc.GetAllocator());
    arr2.PushBack(arr1, doc.GetAllocator());

    rapidjson::Value arr3;
    arr3.SetArray();
    arr3.PushBack(ss, doc.GetAllocator());
    arr3.PushBack(s, doc.GetAllocator());

    rapidjson::Value obj;
    obj.SetObject();
    obj.AddMember(rapidjson::StringRef("abcdef"), ss, doc.GetAllocator());
    obj.AddMember(rapidjson::StringRef("bcdefg"), s, doc.GetAllocator());
    obj.AddMember(rapidjson::StringRef("cdefgh"), arr3, doc.GetAllocator());

    return 0;
}
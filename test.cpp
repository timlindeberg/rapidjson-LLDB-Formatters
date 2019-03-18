#include <vector>
#include "rapidjson/document.h"
#include "rapidjson/stringbuffer.h"
#include "rapidjson/writer.h"

int main() {
    auto json = R"(
    {
        "int": 1,
        "float": 2.0,
        "true": true,
        "false": false,
        "null": null,
        "array": [1, "2", 3],
        "string": "«ταБЬℓσ»: 1<2 & 4+1>3, now 20% off! 😎",
        "smallString": "ABC",
        "smallUtfString": "😎",
        "object": {
            "A": 1,
            "🆔": 2,
            "C": {
                "1": 1,
                "2": [
                    {
                        "a": 1,
                        "b": "A"
                    },
                    {
                        "c": 2,
                        "d": "B"
                    }
                ],
                "3": 3
            }
        }
    }
    )";

    rapidjson::Document doc;
    doc.SetObject();
    doc.Parse(json);

    const rapidjson::Document& docRef = doc;
    const rapidjson::Value& valueRef = doc;
    auto* docPointer = &doc;
    rapidjson::Value* valuePointer = &doc;

    rapidjson::Value t;
    t.SetBool(true);
    rapidjson::Value f;
    f.SetBool(false);
    rapidjson::Value n;
    n.SetNull();
    rapidjson::Value i;
    i.SetInt(-1);
    rapidjson::Value u;
    u.SetUint(2);
    rapidjson::Value i64;
    i64.SetInt64(-123456789012345LL);
    rapidjson::Value u64;
    u64.SetUint64(234567890123456LL);
    rapidjson::Value fl;
    fl.SetFloat(5.5);
    rapidjson::Value d;
    d.SetDouble(6.6);
    rapidjson::Value s1;
    s1.SetString("😎", doc.GetAllocator());
    rapidjson::Value s2;
    s2.SetString(rapidjson::StringRef("ABC12345678910ABC12345678910ABC12345678910ABC12345678910ABC12345678910"));
    rapidjson::Value s3;

    s3.SetString("«ταБЬℓσ»: 1<2 & 4+1>3, now 20% off! 😎", doc.GetAllocator());
    rapidjson::Value s4;
    s4.SetString("12345", 5);
    rapidjson::Value s5;
    s5.SetString(rapidjson::StringRef("Lorem ipsum dolor sit 💺💺 amet, consectetur adipiscing elit. Nam 🇻🇳🇻🇳🇻🇳 gravida commodo aliquam. Aliquam purus sapien, suscipit vel ligula vulputate, molestie tristique justo. Nam 🇻🇳🇻🇳🇻🇳 tincidunt, sem nec aliquam placerat, enim diam sodales metus, ut vulputate lorem dolor imperdiet elit. Aenean rutrum velit et 🇪🇹🇪🇹 lorem tempus porta. Aenean dictum euismod mauris, ac interdum neque pharetra vitae. Ut porttitor velit neque, non commodo tellus aliquam sed. Duis id 🆔 condimentum magna. Quisque facilisis purus nisi, viverra consequat tortor fermentum in. Aliquam lobortis sapien nec ornare porta. Suspendisse erat leo ♌, gravida at dui dictum, scelerisque commodo libero. Etiam laoreet, lorem sit 💺💺 amet mattis posuere, nisl tellus blandit felis, in vulputate arcu eros in ligula. Ut quam enim, hendrerit non felis ac, vestibulum iaculis justo. Ut quis justo id 🆔🆔🆔 metus convallis consectetur aliquet vel lacus. Aliquam cursus erat elit, et 🇪🇹 interdum dui consectetur eget. Sed feugiat ipsum augue, id 🆔 dictum risus maximus a. Fusce pretium metus at eros ultricies porta."));

    rapidjson::Value arr1;
    arr1.SetArray();
    arr1.PushBack(t, doc.GetAllocator());
    arr1.PushBack(f, doc.GetAllocator());
    arr1.PushBack(n, doc.GetAllocator());

    rapidjson::Value arr2;
    arr2.SetArray();
    arr2.PushBack(i, doc.GetAllocator());
    arr2.PushBack(arr1, doc.GetAllocator());
    arr2.PushBack(u64, doc.GetAllocator());

    rapidjson::Value obj1;
    obj1.SetObject();
    obj1.AddMember(rapidjson::StringRef("myFloat"), fl, doc.GetAllocator());
    obj1.AddMember(rapidjson::StringRef("myArray"), arr2, doc.GetAllocator());
    obj1.AddMember(rapidjson::StringRef("myDouble"), d, doc.GetAllocator());

    rapidjson::Value arr3;
    arr3.SetArray();
    arr3.PushBack(s1, doc.GetAllocator());
    arr3.PushBack(s2, doc.GetAllocator());
    arr3.PushBack(obj1, doc.GetAllocator());

    auto array = arr3.GetArray();


    rapidjson::Value obj2;
    obj2.SetObject();
    obj2.AddMember(rapidjson::StringRef("myUnsigned"), u, doc.GetAllocator());
    obj2.AddMember(s3, s4, doc.GetAllocator());
    obj2.AddMember(rapidjson::StringRef("myArray"), arr3, doc.GetAllocator());
    obj2.AddMember(rapidjson::StringRef("myInt64"), i64, doc.GetAllocator());

    auto object = obj2.GetObject();

    std::vector<rapidjson::Value> v;
    v.push_back(std::move(obj2));
    v.push_back(std::move(doc));

    rapidjson::GenericDocument<rapidjson::ASCII<>> asciiDoc;
    asciiDoc.SetObject();
    rapidjson::GenericValue<rapidjson::ASCII<>> utf16int;
    utf16int.SetInt(5);
    rapidjson::GenericValue<rapidjson::ASCII<>> asciiArray;
    asciiArray.SetArray();
    asciiArray.PushBack(utf16int, asciiDoc.GetAllocator());

    asciiDoc.AddMember(rapidjson::StringRef("myASCIIArray"), asciiArray, asciiDoc.GetAllocator());

    return 0;
}
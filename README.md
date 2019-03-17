# rapidjson-LLDB-Formatters
Provides an LLDB data formatter for the [rapidjson](https://github.com/Tencent/rapidjson) library.
The formatter works for the following types:

* `rapidjson::GenericDocument<>`
* `rapidjson::GenericValue<>`
* `rapidjson::GenericArray<>`
* `rapidjson::GenericObject<>`
    
Tested on Mac OSX with `python 2.7`.

# Example

```c++
rapidjson::Document doc;
doc.SetObject();
doc.Parse(R"(
{
    "int": 1,
    "float": 2.0,
    "true": true,
    "false": false,
    "null": null,
    "array": [1, 2, 3],
    "string": "«ταБЬℓσ»: 1<2 & 4+1>3, now 20% off! 😎",
    "object": {
        "A": 1,
        "🆔": 2,
        "C": {
            "1": 1,
            "2": [
                {
                    "a": 1,
                    "b": 2
                },
                {
                    "c": 3,
                    "d": 4
                }
            ],
            "3": 3
        }
    }
}
)");
```

Without the data formatter:
```
(lldb) p doc
(rapidjson::Document) $0 = {
  rapidjson::GenericValue<rapidjson::UTF8<char>, rapidjson::MemoryPoolAllocator<rapidjson::CrtAllocator> > = {
    data_ = {
      s = (length = 8, hashcode = 8, str = <no value available>)
      ss = {
        str = ([0] = 8 '\b', [1] = 0 '\0', [2] = 0 '\0', [3] = 0 '\0', [4] = 8 '\b', [5] = 0 '\0', [6] = 0 '\0', [7] = 0 '\0', [8] = -32 '\xe0', [9] = 21 '\x15', [10] = -128 '\x80', [11] = -17 '\xef', [12] = -75 '\xb5', [13] = 127 '\x7f')
      }
      n = {
        i = (i = 8, padding = char [4] @ 0x00007f911682fcb4)
        u = (u = 8, padding2 = char [4] @ 0x00007f911682fcb4)
        i64 = 34359738376
        u64 = 34359738376
        d = 1.6975966331674704E-313
      }
      o = {
        size = 8
        capacity = 8
        members = 0x00037fb5ef8015e0
      }
      a = {
        size = 8
        capacity = 8
        elements = 0x00037fb5ef8015e0
      }
      f = (payload = char [14] @ 0x00007f911682fcb0, flags = 3)
    }
  }
  allocator_ = 0x00007fb5ef401f30
  ownAllocator_ = 0x00007fb5ef401f30
  stack_ = {
    allocator_ = 0x00007fb5ef400080
    ownAllocator_ = 0x00007fb5ef400080
    stack_ = 0x0000000000000000 <no value available>
    stackTop_ = 0x0000000000000000 <no value available>
    stackEnd_ = 0x0000000000000000 <no value available>
    initialCapacity_ = 1024
  }
  parseResult_ = (code_ = kParseErrorNone, offset_ = 0)
}
```

With the data formatter:

```
(lldb) p doc
(rapidjson::Document) $0 = <Object> size=8 {
  "int" = <Int> 1
  "float" = <Double> 2
  "true" = true
  "false" = false
  "null" = null
  "array" = <Array> size=3 {
    [0] = <Int> 1
    [1] = <Int> 2
    [2] = <Int> 3
  }
  "string" = "«ταБЬℓσ»: 1<2 & 4+1>3, now 20% off! 😎"
  "object" = <Object> size=3 {
    "A" = <Int> 1
    "🆔" = <Int> 2
    "C" = <Object> size=3 {
      "1" = <Int> 1
      "2" = <Array> size=2 {
        [0] = <Object> size=2 {
          "a" = <Int> 1
          "b" = <Int> 2
        }
        [1] = <Object> size=2 {
          "c" = <Int> 3
          "d" = <Int> 4
        }
      }
      "3" = <Int> 3
    }
  }
}
```

It also works out of the box in CLion:
![](https://user-images.githubusercontent.com/6010314/54489916-9f44ac80-48b1-11e9-981a-816aeb8464e1.png "LLDB data formatter for rapidjson in CLion")

# Installation
* Download [rapidjson_formatter.py](https://raw.githubusercontent.com/timlindeberg/rapidjson-LLDB-Formatters/master/rapidjson_formatter.py)
* Create a file called `.lldbinit` in your home folder with the following content:

    ```command script import <PATH>/<TO>/rapidjson_formatter.py```
    
* Done!

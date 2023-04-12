fixresources
============

Introduction
------------
`fixresources` was created to help resolve resource identifiers in disassembled Android application files (smali files).  For more information on this topic, check out Jake Valetta's [blog](http://blog.thecobraden.com/2013/04/fixing-resource-identifiers-in.html).

Usage
-----
`fixresources.py` can now be used directly with python3 from the command line without the `dtf` module. After disassembling an application, you can use it as follows to enrich your smali code:
```bash
pip3 install requirements.txt
python3 fixresources.py path/to/app_root
```


`fixresources` was originally meant to be used as a `dtf` module. After disassembling a application, you can use it as follows to enrich your smali code:

```bash
dtf fixresources path/to/app_root
```

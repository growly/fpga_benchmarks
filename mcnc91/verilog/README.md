These files are generated by ABC with the simple script:

```
read_blif x.blif
write_blif x.v
```

For reasons as-yet-uncovered, the token names generated confuse Vivado when finding module names. '\C17.iscas', for example, causes Vivado to search for 'C17.iscas' (without the backslash), which it cannot find. Such signals have been renamed. This `sed` command will rename modules:

```
sed -i -re 's/^(module )\?([[:alpha:][:digit:]]+)[./]+([[:alpha:][:digit:]]+)/\1\2_\3/g' *.v
```

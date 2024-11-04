file = "txtql.txt"
def redirect(c:str):
    global file
    file = c
def new_cache(name:str, columns:list, funcs:list=[], legacy:bool=False):
    conn = open(file, "r")
    lines = conn.readlines()
    counter = 0
    new_columns = []
    if legacy:
        pass
    else:
        for column in columns:
            a = columns[counter] + '@' + funcs[counter]
            new_columns.append(a)
    for line in lines:
        if "--$" + name in line:
            return "Error: cache already exists"
    conn.close()
    conn = open(file, "a")
    ext = "--$" + name
    if legacy:
        for column in columns:
            if len(column.split("@")) == 1:
                return "Error: column function not defined"
            ext = ext + "!" + column
    else:
        for column in new_columns:
            if len(column.split("@")) == 1:
                return "Error: column function not defined"
            ext = ext + "!" + column
    conn.write(ext + "\n")
    conn.close()
    return "Success: cache created"
def wipe():
    conn = open(file, "w")
    conn.close()
    print("Success: caches wiped")
    return "Success: caches wiped"
def get_columns(line:str, de:bool=False, func:bool=False):
    c = line.split("!")
    if not de:
        c.remove(c[0])
    new = []
    if not func:
        for v in c:
            new.append(v.split("@")[0])
    if not new:
        return c
    else:
        return new
def secure(data:str, replacewith:str="[ATTEMPTED INJECTION]"):
    data = data.replace("--$", replacewith)
    data = data.replace("--&", replacewith)
    data = data.replace("!", replacewith)
    return data
def is_secure(data:str):
    if secure(data) != data:
        return False
    else:
        return True
def get_cache_data(cache:str, funcs:bool=False):
    conn = open(file, "r")
    lines = conn.readlines()
    active = None
    for line in lines:
        if "--$" + cache in line:
            active = line
    if not active:
        return "Error: cache not found"
    ret = get_columns(active, False, funcs)
    for re in ret:
        if re.removesuffix("\n") != re:
            ret.remove(re)
            ret.append(re.removesuffix("\n"))
    return ret
def insert(cache:str, values:list):
    conn = open(file, "r")
    lines = conn.readlines()
    active = None
    for line in lines:
        if "--$" + cache in line:
            active = line
    if not active:
        return "Error: cache not found"
    columns = active.split("!")
    columns.remove(columns[0])
    ext = "--&" + cache
    counter = 0
    for column in columns:
        ext = ext + "!" + str(values[counter])
        counter += 1
    conn.close()
    conn = open(file, "a")
    conn.write(ext + "\n")
    conn.close()
    global last_cache
    last_cache = cache
    return "Success: inserted values to cache"
def select(cache:str, vals="*"):
    conn = open(file, "r")
    lines = conn.readlines()
    active = None
    for line in lines:
        if "--$" + cache in line:
            active = line
            linedefs = get_columns(line, False, False)
    if not active:
        return "Error: cache not found"
    columns = active.split("!")
    columns.remove(columns[0])
    index = []
    if vals != "*":
        for val in vals:
            if val in linedefs:
                index.append(linedefs.index(val))
            else:
                return "Error: column not found"
    valid = []
    for line in lines:
        if "--&" + cache in line:
            valid.append(line)
    ret = []
    for val in valid:
        c = val.split("!")
        c.remove(c[0])
        add = []
        counter = 0
        for v in c:
            if len(index) != 0:
                if counter not in index:
                    counter += 1
                else:
                    if columns[counter].split("@")[1] == "str" or columns[counter].split("@")[1] == "str\n":
                        if "\n" in v:
                            add.append(v.split("@")[0].removesuffix("\n"))
                            counter += 1
                        else:
                            add.append(v.split("@")[0])
                            counter += 1
                    else:
                        if "\n" in v:
                            add.append(int(v.split("@")[0].removesuffix("\n")))
                            counter += 1
                        else:
                            add.append(int(v.split("@")[0]))
                            counter += 1
            else:
                if columns[counter].split("@")[1] == "str" or columns[counter].split("@")[1] == "str\n":
                    if "\n" in v:
                        add.append(v.split("@")[0].removesuffix("\n"))
                        counter += 1
                    else:
                        add.append(v.split("@")[0])
                        counter += 1
                else:
                    if "\n" in v:
                        add.append(int(v.split("@")[0].removesuffix("\n")))
                        counter += 1
                    else:
                        add.append(int(v.split("@")[0]))
                        counter += 1
        ret.append(add)
    return ret
def alter(cache:str, vals:list, funcs:list):    
    conn = open(file, "r")
    lines = conn.readlines()
    active = None
    for line in lines:
        if "--$" + cache in line:
            active = line
            lines.remove(line)
    if not active:
        return "Error: cache not found"
    for val in vals:
        active = active.removesuffix("\n")
        active = active + "!" + val + "@" + funcs[vals.index(val)]
    active = active + "\n"
    conn.close()
    conn = open(file, "w")
    for line in lines:
        conn.write(line)
    conn.write(active)
    conn.close()
    return "Success: cache altered"
def destroy(cache:str):
    conn = open(file, "r")
    lines = conn.readlines()
    toremove = []
    for line in lines:
        if "--$" + cache in line or "--&" + cache in line:
            toremove.append(line)
    conn.close()
    conn = open(file, "w")
    for line in lines:
        if line in toremove:
            pass
        else:
            conn.write(line)
    conn.close()
    return "Success: cache removed"
def cleanse(cache:str):
    conn = open(file, "r")
    lines = conn.readlines()
    toremove = []
    for line in lines:
        if "--&" + cache in line:
            toremove.append(line)
    conn.close()
    conn = open(file, "w")
    for line in lines:
        if line in toremove:
            pass
        else:
            conn.write(line)
    conn.close()
    return "Success: cache cleansed"
def count(cache:str):
    conn = open(file, "r")
    lines = conn.readlines()
    counter = 0
    for line in lines:
        if "--&" + cache in line:
            counter += 1
    return counter
def where(data:list, whereColumn:str, whereEquals, cache):
    dataret = get_cache_data(cache)
    dat = -1
    for dat in dataret:
        if dat == whereColumn:
            index = dataret.index(dat)
    if index == -1:
        return "Error: column not found"
    corr = []
    for d in data:
        check = d[index]
        if str(check) == str(whereEquals):
            corr.append(d)
    return corr

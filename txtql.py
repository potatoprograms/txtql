#!/usr/bin/env python3

CASE_SENSITIVE = False  # Set True for case-sensitive matching
cs = CASE_SENSITIVE #runtime editable copy

def tokenize(query: str):
    """
    Split the input into tokens, preserving quoted strings (single or double quotes).
    Returns a list of tokens (quotes removed).
    """
    tokens = []
    curr = ""
    in_quote = False
    quote_char = None
    i = 0
    while i < len(query):
        ch = query[i]
        if in_quote:
            if ch == quote_char:
                tokens.append(curr)
                curr = ""
                in_quote = False
                quote_char = None
            else:
                curr += ch
        else:
            if ch in ("'", '"'):            # begin quote
                in_quote = True
                quote_char = ch
                if curr:
                    tokens.append(curr)
                    curr = ""
            elif ch.isspace():
                if curr:
                    tokens.append(curr)
                    curr = ""
            else:
                curr += ch
        i += 1
    if curr:
        tokens.append(curr)
    return tokens

def parse(tokens):
    global cs
    """
    Parse tokens into a small AST (dict):
      { "command": "select", "file": "<filename>", "conditions": [ {type, value, connector}, ... ] }
    Connector is the token AFTER the condition (i.e., the connector that joins this condition to the next one).
    """
    if not tokens:
        raise ValueError("Empty query")
    if tokens[0].lower() != "select":
        raise ValueError("Query must start with 'select'")
    if tokens[-1].lower() == "casesensitive":
        cs = True
        del tokens[-1]
    # find "from"
    from_idx = None
    for i, t in enumerate(tokens):
        if t.lower() == "from":
            from_idx = i
            break
    if from_idx is None:
        raise ValueError("Missing 'from' keyword")

    if from_idx + 1 >= len(tokens):
        raise ValueError("Missing filename after 'from'")
    filename = tokens[from_idx + 1]

    # parse conditions beginning after the filename
    i = from_idx + 2
    conditions = []
    tweaks = []
    negated = False
    allowed = {"containing", "starting", "ending", "length", "hasword", "wordcount"}
    allowedTweaks = {"unique", "duplicate", "reverse", "limit","offset"}
    count = None
    count_eq = None
    def is_integerable(s):
        try:
            int(s)
            return True
        except ValueError:
            return False
    while i < len(tokens):
        keyword = tokens[i].lower()
        if keyword in allowedTweaks:
            if keyword == 'limit' or keyword == "offset":
                if i+1 < len(tokens):
                    if is_integerable(tokens[i+1]):
                        keyword = f"{keyword}_{tokens[i+1]}"
                        i += 1
                    else:
                        raise ValueError("Tweak count is not a number")
                else:
                    raise ValueError("Tweak missing count.")
            tweaks.append(keyword)
            i += 1
            continue
        i_offset = 1

        if keyword in ("and", "or"):
            i += 1
            continue
        if keyword == "not":
            negated = True
            i += 1
            continue

        if i + 1 >= len(tokens):
            raise ValueError(f"Missing value for condition '{tokens[i]}'")
        value = tokens[i+1]

        if value in ("=", "<", ">", ">=", "<="):
            count = int(tokens[i+2])
            count_eq = value
            if keyword not in ("length", "wordcount"):
                value = tokens[i+3]
            i_offset = 4
        elif '"' not in value and value.isdigit():
            count = int(value)
            count_eq = "="
            if keyword != "length":
                value = tokens[i+2]
                i_offset = 3
        else:
            i_offset = 2

        # check for connector
        connector = None
        if i + i_offset < len(tokens) and tokens[i + i_offset].lower() in ("and", "or"):
            connector = tokens[i + i_offset].lower()
            i_offset += 1

        if keyword not in allowed:
            raise ValueError(f"Unknown condition type '{keyword}'. Allowed: {', '.join(sorted(allowed))}")

        conditions.append({
            "type": keyword,
            "value": value,
            "connector": connector,
            "negated": negated,
            "count": count,
            "count_eq": count_eq
        })

        i += i_offset
        negated = False
        count = None
        count_eq = None
    return {"command": "select", "file": filename, "conditions": conditions, "tweaks":tweaks}

def evaluate_select(parsed, case_sensitive=cs):
    """
    Apply parsed conditions to the named file and return matching lines.
    Boolean evaluation is left-to-right using connectors stored on each condition (connector joins this condition to the next).
    """
    filename = parsed["file"]
    try:
        with open(filename, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except Exception as e:
        raise RuntimeError(f"Could not open file '{filename}': {e}")

    def match(cond, line, allLines):
        t = cond["type"].lower()
        v = cond["value"]
        if t not in ("unique", "duplicate"):
            if not case_sensitive:
                line_cmp = line.lower()
                v_cmp = v.lower()
            else:
                line_cmp = line
                v_cmp = v
        else:
            line_cmp = line
            v_cmp = None
        res = None
        ops = {
            "=": lambda a,b: a == b,
            ">": lambda a,b: a > b,
            "<": lambda a,b: a < b,
            ">=": lambda a,b: a >= b,
            "<=": lambda a,b: a <= b,
            }

        if t == "containing":
            line_cnt = line_cmp.count(v_cmp)
            count_eq = cond["count_eq"]
            if cond["count"] == None:
                res = line_cnt > 0
            else:
                res = ops[count_eq](line_cnt, cond["count"])
        elif t == "starting":
            res = line_cmp.startswith(v_cmp)
        elif t == "ending":
            res = line_cmp.rstrip("\n").endswith(v_cmp)
        elif t == "length":
            if cond["count_eq"] == None:
                res = len(line_cmp.rstrip("\n")) == cond["count"]
            else:
                res = ops[cond["count_eq"]](len(line_cmp.rstrip("\n")), cond["count"])
        elif t == "hasword":
            if cond["count"] == None:
                res = v_cmp in line_cmp.rstrip("\n").split(" ")
            else:
                res = ops[cond["count_eq"]](len([word for word in line_cmp.rstrip("\n").split(" ") if word == v_cmp]), cond["count"])
        elif t == "wordcount":
            if cond["count_eq"] == None:
                res = len(line_cmp.rstrip("\n").split(" ")) == cond['count']
            else:
                res = ops[cond["count_eq"]](len(line_cmp.rstrip("\n").split(" ")), cond['count'])
        # shouldn't reach here due to parse validation
        else:
            return False
        return res ^ cond["negated"]

    mask = None            # boolean list of same length as lines
    prev_connector = None  # connector that joined previous condition to this one

    for cond in parsed["conditions"]:
        current = [match(cond, ln, [ln.rstrip('\n') for ln in lines]) for ln in lines]
        if mask is None:
            # first condition => start the mask
            mask = current
        else:
            # combine mask with current according to the PREVIOUS connector
            if prev_connector == "and":
                mask = [a and b for a, b in zip(mask, current)]
            elif prev_connector == "or":
                mask = [a or b for a, b in zip(mask, current)]
            else:
                # fallback (shouldn't happen) — replace mask
                mask = current
        # store connector that follows this condition (used to join to the next)
        prev_connector = cond.get("connector")

    # if there were no conditions, return all lines
    res = [ln for ln, ok in zip(lines, mask) if ok] if mask else lines
    for tweak in parsed['tweaks']:
        if tweak == 'unique':
            res = [ln for ln in res if lines.count(ln) == 1]
        elif tweak == 'duplicate':
            res = [ln for ln in res if lines.count(ln) > 1]
        elif tweak == "reverse":
            res.reverse()
        elif tweak.startswith("limit_"):
            res = res[:int(tweak.split("_",1)[1])]
        elif tweak.startswith("offset_"):
            res = res [int(tweak.split("_", 1)[1]):]
    return res

def run_interactive():
    banner = (
        "Tiny text-query runner.\n"
        "Enter queries like:\n"
        "  select line from data.txt containing 'error' and starting 'WARN'\n"
        "  select line from \"my logs.txt\" containing 'timeout' or ending 'failed'\n"
        "Type 'quit' or 'exit' to leave.\n"
    )
    print(banner)
    global cs
    while True:
        try:
            q = input("Query> ").strip()
            if not q:
                continue
            if q.lower() in ("quit", "exit"):
                print("bye!")
                break
            toks = tokenize(q)
            parsed = parse(toks)
            results = evaluate_select(parsed, cs)
            if results:
                print("".join(results), end="")  # lines already contain newlines
            else:
                print("(no matching lines)")
        except Exception as exc:
            print("Error:", exc)
        cs = CASE_SENSITIVE
if __name__ == "__main__":
    run_interactive()
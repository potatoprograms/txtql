#!/usr/bin/env python3
"""
Tiny SQL-ish text query tool (single-file).
Syntax:
  select line from <filename> [ <criteria> ... ]
Criteria:
  containing 'text'
  starting 'text'
  ending 'text'
Connectors:
  and, or

Examples:
  select line from data.txt containing 'error' and starting 'WARN'
  select line from "my log.txt" containing 'timeout' or ending 'failed'
Notes:
  - Values with spaces must be quoted with single or double quotes.
  - Matching is case-insensitive by default. Change CASE_SENSITIVE below if you want otherwise.
"""

CASE_SENSITIVE = False  # Set True for case-sensitive matching

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
    """
    Parse tokens into a small AST (dict):
      { "command": "select", "file": "<filename>", "conditions": [ {type, value, connector}, ... ] }
    Connector is the token AFTER the condition (i.e., the connector that joins this condition to the next one).
    """
    if not tokens:
        raise ValueError("Empty query")
    if tokens[0].lower() != "select":
        raise ValueError("Query must start with 'select'")

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
    negated = False
    allowed = {"containing", "starting", "ending", "length"}
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

        if keyword in ("and", "or"):
            # stray connector (malformed). Skip it to be forgiving.
            i += 1
            continue
        if keyword == "not":
            #acknowledge and continue
            negated = True
            i += 1
            continue
        if i + 1 >= len(tokens):
            raise ValueError(f"Missing value for condition '{tokens[i]}'")
        value = tokens[i + 1]
        if value in ("=", "<", ">", ">=", "<="):
            count = int(tokens[i+2])
            count_eq = value
            if keyword != "length":
                value = tokens[i+3]
            i_offset = 4
        elif '"' not in value and is_integerable(value):
            count = int(value)
            count_eq = "="
            if keyword != "length":
                value = tokens[i+2]
            i_offset = 3
        else:
            i_offset = 2
        connector = None
        if i + i_offset < len(tokens) and tokens[i + i_offset].lower() in ("and", "or"):
            connector = tokens[i + i_offset].lower()
            i_offset += 1
        if keyword not in allowed:
            raise ValueError(f"Unknown condition type '{keyword}'. Allowed: {', '.join(sorted(allowed))}")
        conditions.append({"type": keyword, "value": value, "connector": connector, "negated": negated, "count":count, "count_eq":count_eq})
        i += i_offset
        negated = False
        count = None
        count_eq = None
    return {"command": "select", "file": filename, "conditions": conditions}

def evaluate_select(parsed, case_sensitive=CASE_SENSITIVE):
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

    def match(cond, line):
        t = cond["type"].lower()
        v = cond["value"]
        if not case_sensitive:
            line_cmp = line.lower()
            v_cmp = v.lower()
        else:
            line_cmp = line
            v_cmp = v
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
        # shouldn't reach here due to parse validation
        else:
            return False
        return res ^ cond["negated"]

    mask = None            # boolean list of same length as lines
    prev_connector = None  # connector that joined previous condition to this one

    for cond in parsed["conditions"]:
        current = [match(cond, ln) for ln in lines]
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
    if mask is None:
        return lines

    return [ln for ln, ok in zip(lines, mask) if ok]

def run_interactive():
    banner = (
        "Tiny text-query runner.\n"
        "Enter queries like:\n"
        "  select line from data.txt containing 'error' and starting 'WARN'\n"
        "  select line from \"my logs.txt\" containing 'timeout' or ending 'failed'\n"
        "Type 'quit' or 'exit' to leave.\n"
    )
    print(banner)
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
            results = evaluate_select(parsed)
            if results:
                print("".join(results), end="")  # lines already contain newlines
            else:
                print("(no matching lines)")
        except Exception as exc:
            print("Error:", exc)

if __name__ == "__main__":
    run_interactive()

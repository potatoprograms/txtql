def tokenize(line):
    tokens = []
    curr = ""
    in_str = False
    for char in line:
        if char == "'":
            if in_str:
                tokens.append(curr)
                curr = ""
                in_str = False
            else:
                in_str = True
        elif char == " " and not in_str:
            if curr:  # avoid empty tokens
                tokens.append(curr)
            curr = ""
        else:
            curr += char
    if curr:  # grab last token
        tokens.append(curr)
    return tokens

def selectLine(tokens):
    file = tokens[3]
    with open(file) as f:
        lines = f.readlines()

    if len(tokens) < 4:
        return lines

    i = 4
    criteria = []
    while i <= len(tokens) - 2:
        keyword = tokens[i]
        searchingFor = tokens[i+1]
        connector = tokens[i+2] if len(tokens) >= i+3 else None
        criteria.append([keyword, searchingFor, connector])
        i += 3
    def applyCriteria(c, l):
        if c[0] == "containing":
            l = [c[1] in s for s in l]
        elif c[0] == "starting":
            l = [s.startswith(c[1]) for s in l]
        elif c[0] == "ending":
            l = [s.rstrip("\n").endswith(c[1]) for s in l]
        return l
    print(criteria)
    stack = []
    lastConnector = ""
    for criterion in criteria:
        if not lastConnector:
            stack = applyCriteria(criterion, lines)
        else:
            ourStack = applyCriteria(criterion, lines)
            if lastConnector == "and":
                stack = [a and b for a, b in zip(stack, ourStack)]
            elif lastConnector == "or":
                stack = [a or b for a, b in zip(stack, ourStack)]
        lastConnector = criterion[2] if len(criterion) > 2 else ""
    lines = [line for line, b in zip(lines, stack) if b]
    return lines
print(selectLine(tokenize(input(""))))
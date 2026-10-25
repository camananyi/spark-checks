import ast
import io
import multiprocessing
import re
import sys
import tokenize

import check50

# Python 3.14 switched Linux to "forkserver" processes, which breaks check50 3.5.0; go back to "fork"
if sys.platform != "win32":
    multiprocessing.set_start_method("fork", force=True)

FILE = "week1_aboutme.py"
# Numeric test answers, so programs that use int() or float() on an input still work
ANSWERS = ["4711", "5823", "6934", "7045", "8156", "9267", "1378", "2489"]
# Variable names that technically work but don't describe what they hold
VAGUE = re.compile(r"^([a-z]|[a-z]\d+|var\d*|variable\d*|input\d*|answer\d*|x\d*|temp\d*|thing\d*)$", re.I)
FILLER_COMMENT = re.compile(r"^#\s*(line\s*\d*|code|comment|todo|\d+|stuff|here)?\s*$", re.I)


def _tree():
    with open(FILE) as f:
        return ast.parse(f.read())


def _input_calls(tree):
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "input"]


def _stored_inputs(tree):
    """Names of variables that receive input(), including int(input()) and similar."""
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _input_calls(node.value):
            names += [t.id for t in node.targets if isinstance(t, ast.Name)]
    return names


@check50.check()
def exists():
    """week1_aboutme.py exists"""
    check50.exists(FILE)


@check50.check(exists)
def compiles():
    """week1_aboutme.py has no syntax errors"""
    try:
        _tree()
    except SyntaxError as e:
        raise check50.Failure(f"Python couldn't read your file: line {e.lineno}: {e.msg}",
                              help="Check that line for a missing quote, bracket, or colon.")


@check50.check(compiles)
def asks_four_questions():
    """asks the user for at least 4 pieces of information using input()"""
    count = len(_input_calls(_tree()))
    if count < 4:
        raise check50.Failure(f"found {count} input() call(s), expected at least 4",
                              help="Add more questions with input() until you have at least 4.")


@check50.check(compiles)
def stores_in_named_variables():
    """stores each answer in a clearly named variable"""
    tree = _tree()
    stored = _stored_inputs(tree)
    if len(stored) < len(_input_calls(tree)):
        raise check50.Failure("at least one input() is not saved in a variable",
                              help="Write each question like: favorite_food = input(\"What is your favorite food? \")")
    vague = [n for n in stored if VAGUE.match(n)]
    if vague:
        raise check50.Failure(f"these variable names don't describe what they hold: {', '.join(vague)}",
                              help="Use names like first_name or favorite_color instead of x or var1.")


@check50.check(compiles)
def runs_without_errors():
    """program runs without any errors"""
    n = len(_input_calls(_tree()))
    proc = check50.run(f"python3 {FILE}")
    for answer in ANSWERS[:n]:
        proc.stdin(answer, prompt=False)
    try:
        proc.exit(0, timeout=10)
    except check50.Failure:
        # Swap check50's "expected exit code 0, not 1" for a message a beginner can act on
        raise check50.Failure("your program crashed before it finished",
                              help="Run python3 week1_aboutme.py yourself, answer the questions, and read the last line of the red error message.")


@check50.check(runs_without_errors)
def prints_paragraph_with_answers():
    """prints a short paragraph that uses every answer"""
    n = len(_input_calls(_tree()))
    proc = check50.run(f"python3 {FILE}")
    for answer in ANSWERS[:n]:
        proc.stdin(answer, prompt=False)
    output = proc.stdout(timeout=10)

    missing = [a for a in ANSWERS[:n] if a not in output]
    if missing:
        raise check50.Failure(f"{len(missing)} of your {n} answers never showed up in what the program printed",
                              help="Make sure every variable is used in your print() paragraph.")

    # A paragraph needs real sentences around the answers, not just the answers themselves
    words = re.findall(r"[A-Za-z']+", output)
    if len(words) < 15:
        raise check50.Failure("the output looks like raw variables, not a paragraph",
                              help="Write full sentences around your variables, e.g. print(f\"My name is {name} and I love {food}.\")")


@check50.check(compiles)
def has_comments():
    """has at least 2 meaningful comments"""
    with open(FILE) as f:
        tokens = tokenize.generate_tokens(io.StringIO(f.read()).readline)
        comments = [t.string for t in tokens if t.type == tokenize.COMMENT]
    meaningful = [c for c in comments
                  if not FILLER_COMMENT.match(c) and len(re.findall(r"[A-Za-z]+", c)) >= 3]
    if len(meaningful) < 2:
        raise check50.Failure(f"found {len(meaningful)} meaningful comment(s), expected at least 2",
                              help="Explain what your code does, e.g. # this asks the user for their name")

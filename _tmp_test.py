
import re
ptn1 = r"(?<!\)\("  # wrong approach, just use the raw string directly
# Use the exact pattern from the source
ptn1 = r"(?<!\)\("
# Actually let me just compile then test:
p = re.compile(r"(?<!\)\(")
# Single backslash + paren
s1 = chr(92) + chr(40)  # backslash + (
print("s1 chars:", list(s1))
print("s1 flagged:", bool(p.search(s1)))
# Double backslash + paren
s2 = chr(92)+chr(92) + chr(40)
print("s2 chars:", list(s2))
print("s2 flagged:", bool(p.search(s2)))

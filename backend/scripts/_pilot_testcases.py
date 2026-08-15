"""Pilot batch: reference solutions + additional test calls for 6 technical
questions with thin (2-3 case) test coverage. Every additional call below was
chosen to be simple enough to hand-trace, as a sanity check alongside the
sandbox execution that actually produces the persisted `expected` value (see
repair_question_bank.append_verified_test_case — it never trusts a claimed
value, it executes the call and uses the real result)."""

PILOT = {
    "add-binary": dict(
        reference_solution='''class Solution:
    def addBinary(self, a: str, b: str) -> str:
        return bin(int(a, 2) + int(b, 2))[2:]
''',
        # 0+0=0 -> "0"; 15+15=30 -> "11110" (hand-traced)
        new_calls=['Solution().addBinary(a = "0", b = "0")', 'Solution().addBinary(a = "1111", b = "1111")'],
    ),
    "climbing-stairs": dict(
        reference_solution='''class Solution:
    def climbStairs(self, n: int) -> int:
        if n <= 2:
            return n
        a, b = 1, 2
        for _ in range(3, n + 1):
            a, b = b, a + b
        return b
''',
        # f(1)=1 (base case); f(5): 1,2,3,5,8 -> 8 (hand-traced)
        new_calls=["Solution().climbStairs(n = 1)", "Solution().climbStairs(n = 5)"],
    ),
    "evaluate-reverse-polish-notation": dict(
        reference_solution='''class Solution:
    def evalRPN(self, tokens):
        st = []
        for t in tokens:
            if t in ("+", "-", "*", "/"):
                b = st.pop(); a = st.pop()
                if t == "+": st.append(a + b)
                elif t == "-": st.append(a - b)
                elif t == "*": st.append(a * b)
                else: st.append(int(a / b))
            else:
                st.append(int(t))
        return st[-1]
''',
        # 4-3=1; 2*3=6, 6+4=10 (hand-traced)
        new_calls=['Solution().evalRPN(tokens = ["4","3","-"])', 'Solution().evalRPN(tokens = ["2","3","*","4","+"])'],
    ),
    "largest-number": dict(
        reference_solution='''from functools import cmp_to_key

class Solution:
    def largestNumber(self, nums):
        s = list(map(str, nums))
        s.sort(key=cmp_to_key(lambda x, y: -1 if x + y > y + x else (1 if x + y < y + x else 0)))
        res = "".join(s).lstrip("0")
        return res if res else "0"
''',
        # all-zero edge case -> "0" (not "00"); single element -> "1" (hand-traced)
        new_calls=["Solution().largestNumber(nums = [0,0])", "Solution().largestNumber(nums = [1])"],
    ),
    "max-sum-of-rectangle-no-larger-than-k": dict(
        reference_solution='''import bisect

class Solution:
    def maxSumSubmatrix(self, matrix, k):
        rows, cols = len(matrix), len(matrix[0])
        best = float("-inf")
        for top in range(rows):
            colsum = [0] * cols
            for bottom in range(top, rows):
                for c in range(cols):
                    colsum[c] += matrix[bottom][c]
                sorted_prefix = [0]
                cur = 0
                for v in colsum:
                    cur += v
                    idx = bisect.bisect_left(sorted_prefix, cur - k)
                    if idx < len(sorted_prefix):
                        best = max(best, cur - sorted_prefix[idx])
                    bisect.insort(sorted_prefix, cur)
        return best
''',
        # single cell [1]<=2 -> 1; row [2,2,-1] subarray sums {2,4,3,2,1,-1}, max<=0 -> -1 (hand-traced)
        new_calls=[
            "Solution().maxSumSubmatrix(matrix = [[1]], k = 2)",
            "Solution().maxSumSubmatrix(matrix = [[2,2,-1]], k = 0)",
        ],
    ),
    "russian-doll-envelopes": dict(
        reference_solution='''import bisect

class Solution:
    def maxEnvelopes(self, envelopes):
        envelopes.sort(key=lambda e: (e[0], -e[1]))
        tails = []
        for _, h in envelopes:
            idx = bisect.bisect_left(tails, h)
            if idx == len(tails):
                tails.append(h)
            else:
                tails[idx] = h
        return len(tails)
''',
        # single envelope -> 1; sorted by (w,-h): [1,1],[2,3],[4,6],[4,5],[6,7] -> LIS on h
        # [1,3,6,5,7]: tails 1 -> 1,3 -> 1,3,6 -> 1,3,5 (6 replaced) -> 1,3,5,7 => length 4 (hand-traced)
        new_calls=[
            "Solution().maxEnvelopes(envelopes = [[1,1]])",
            "Solution().maxEnvelopes(envelopes = [[4,5],[4,6],[6,7],[2,3],[1,1]])",
        ],
    ),
}

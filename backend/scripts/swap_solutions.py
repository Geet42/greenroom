"""
Hand-authored reference solutions for the 41 replacement candidates picked by
swap_unsupported_questions.py, keyed by neenza problem_slug. Written directly
rather than LLM-generated (Groq was rate-limited and the Ollama fallback is
less reliable for this) — these are all standard, well-known algorithm
problems where a direct, reasoned implementation is more trustworthy than a
smaller fallback model's guess. Still never trusted blind: the caller runs
each of these through the real sandbox and checks the output against the
dataset's own official example outputs before accepting anything.
"""
from __future__ import annotations

SOLUTIONS: dict[str, str] = {
"median-of-two-sorted-arrays": """
def findMedianSortedArrays(nums1, nums2):
    merged = sorted(nums1 + nums2)
    n = len(merged)
    if n % 2 == 1:
        return float(merged[n // 2])
    return (merged[n // 2 - 1] + merged[n // 2]) / 2.0
""",

"longest-substring-without-repeating-characters": """
def lengthOfLongestSubstring(s):
    seen = {}
    start = 0
    best = 0
    for i, c in enumerate(s):
        if c in seen and seen[c] >= start:
            start = seen[c] + 1
        seen[c] = i
        best = max(best, i - start + 1)
    return best
""",

"longest-palindromic-substring": """
def longestPalindrome(s):
    if not s:
        return ""
    start, end = 0, 0
    def expand(l, r):
        while l >= 0 and r < len(s) and s[l] == s[r]:
            l -= 1
            r += 1
        return l + 1, r - 1
    for i in range(len(s)):
        l1, r1 = expand(i, i)
        if r1 - l1 > end - start:
            start, end = l1, r1
        l2, r2 = expand(i, i + 1)
        if r2 - l2 > end - start:
            start, end = l2, r2
    return s[start:end + 1]
""",

"zigzag-conversion": """
def convert(s, numRows):
    if numRows == 1 or numRows >= len(s):
        return s
    rows = [''] * numRows
    cur, step = 0, 1
    for c in s:
        rows[cur] += c
        if cur == 0:
            step = 1
        elif cur == numRows - 1:
            step = -1
        cur += step
    return ''.join(rows)
""",

"regular-expression-matching": """
def isMatch(s, p):
    memo = {}
    def dp(i, j):
        if (i, j) in memo:
            return memo[(i, j)]
        if j == len(p):
            res = i == len(s)
        else:
            first = i < len(s) and p[j] in (s[i], '.')
            if j + 1 < len(p) and p[j + 1] == '*':
                res = dp(i, j + 2) or (first and dp(i + 1, j))
            else:
                res = first and dp(i + 1, j + 1)
        memo[(i, j)] = res
        return res
    return dp(0, 0)
""",

"longest-valid-parentheses": """
def longestValidParentheses(s):
    stack = [-1]
    best = 0
    for i, c in enumerate(s):
        if c == '(':
            stack.append(i)
        else:
            stack.pop()
            if not stack:
                stack.append(i)
            else:
                best = max(best, i - stack[-1])
    return best
""",

"first-missing-positive": """
def firstMissingPositive(nums):
    n = len(nums)
    nums = nums[:]
    for i in range(n):
        while 1 <= nums[i] <= n and nums[nums[i] - 1] != nums[i]:
            j = nums[i] - 1
            nums[i], nums[j] = nums[j], nums[i]
    for i in range(n):
        if nums[i] != i + 1:
            return i + 1
    return n + 1
""",

"reverse-integer": """
def reverse(x):
    sign = -1 if x < 0 else 1
    x = abs(x)
    result = 0
    while x != 0:
        result = result * 10 + x % 10
        x //= 10
    result *= sign
    if result < -2**31 or result > 2**31 - 1:
        return 0
    return result
""",

"trapping-rain-water": """
def trap(height):
    if not height:
        return 0
    l, r = 0, len(height) - 1
    left_max, right_max = height[l], height[r]
    total = 0
    while l < r:
        if left_max <= right_max:
            l += 1
            left_max = max(left_max, height[l])
            total += left_max - height[l]
        else:
            r -= 1
            right_max = max(right_max, height[r])
            total += right_max - height[r]
    return total
""",

"wildcard-matching": """
def isMatch(s, p):
    m, n = len(s), len(p)
    dp = [[False] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = True
    for j in range(1, n + 1):
        if p[j - 1] == '*':
            dp[0][j] = dp[0][j - 1]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if p[j - 1] == '*':
                dp[i][j] = dp[i - 1][j] or dp[i][j - 1]
            elif p[j - 1] == '?' or p[j - 1] == s[i - 1]:
                dp[i][j] = dp[i - 1][j - 1]
    return dp[m][n]
""",

"n-queens-ii": """
def totalNQueens(n):
    cols, diag1, diag2 = set(), set(), set()
    count = 0
    def backtrack(row):
        nonlocal count
        if row == n:
            count += 1
            return
        for col in range(n):
            if col in cols or (row - col) in diag1 or (row + col) in diag2:
                continue
            cols.add(col); diag1.add(row - col); diag2.add(row + col)
            backtrack(row + 1)
            cols.discard(col); diag1.discard(row - col); diag2.discard(row + col)
    backtrack(0)
    return count
""",

"string-to-integer-atoi": """
def myAtoi(s):
    s = s.strip()
    if not s:
        return 0
    i = 0
    sign = 1
    if s[0] in '+-':
        if s[0] == '-':
            sign = -1
        i += 1
    num = 0
    while i < len(s) and s[i].isdigit():
        num = num * 10 + int(s[i])
        i += 1
    num *= sign
    INT_MIN, INT_MAX = -2**31, 2**31 - 1
    return max(INT_MIN, min(INT_MAX, num))
""",

"permutation-sequence": """
import math
def getPermutation(n, k):
    nums = [str(i) for i in range(1, n + 1)]
    k -= 1
    result = []
    for i in range(n, 0, -1):
        fact = math.factorial(i - 1)
        idx = k // fact
        k %= fact
        result.append(nums.pop(idx))
    return ''.join(result)
""",

"container-with-most-water": """
def maxArea(height):
    l, r = 0, len(height) - 1
    best = 0
    while l < r:
        best = max(best, (r - l) * min(height[l], height[r]))
        if height[l] < height[r]:
            l += 1
        else:
            r -= 1
    return best
""",

"valid-number": """
import re
def isNumber(s):
    pattern = r'^[+-]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][+-]?\\d+)?$'
    return bool(re.match(pattern, s))
""",

"minimum-window-substring": """
from collections import Counter
def minWindow(s, t):
    if not t or not s:
        return ""
    need = Counter(t)
    missing = len(t)
    left = 0
    best_left, best_right = 0, 0
    for right, c in enumerate(s, 1):
        if need[c] > 0:
            missing -= 1
        need[c] -= 1
        if missing == 0:
            while left < right and need[s[left]] < 0:
                need[s[left]] += 1
                left += 1
            if best_right == 0 or right - left < best_right - best_left:
                best_left, best_right = left, right
    return s[best_left:best_right]
""",

"palindrome-number": """
def isPalindrome(x):
    if x < 0:
        return False
    s = str(x)
    return s == s[::-1]
""",

"largest-rectangle-in-histogram": """
def largestRectangleArea(heights):
    stack = []
    best = 0
    for i, h in enumerate(heights + [0]):
        while stack and heights[stack[-1]] >= h:
            height = heights[stack.pop()]
            width = i if not stack else i - stack[-1] - 1
            best = max(best, height * width)
        stack.append(i)
    return best
""",

"integer-to-roman": """
def intToRoman(num):
    vals = [(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),
            (50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]
    result = []
    for v, sym in vals:
        while num >= v:
            result.append(sym)
            num -= v
    return ''.join(result)
""",

"maximal-rectangle": """
def maximalRectangle(matrix):
    if not matrix or not matrix[0]:
        return 0
    n = len(matrix[0])
    heights = [0] * n
    best = 0
    for row in matrix:
        for i in range(n):
            heights[i] = heights[i] + 1 if row[i] == '1' else 0
        stack = []
        for i, h in enumerate(heights + [0]):
            while stack and heights[stack[-1]] >= h:
                height = heights[stack.pop()]
                width = i if not stack else i - stack[-1] - 1
                best = max(best, height * width)
            stack.append(i)
    return best
""",

"scramble-string": """
from functools import lru_cache
def isScramble(s1, s2):
    @lru_cache(maxsize=None)
    def helper(a, b):
        if a == b:
            return True
        if sorted(a) != sorted(b):
            return False
        n = len(a)
        for i in range(1, n):
            if helper(a[:i], b[:i]) and helper(a[i:], b[i:]):
                return True
            if helper(a[:i], b[n - i:]) and helper(a[i:], b[:n - i]):
                return True
        return False
    return helper(s1, s2)
""",

"distinct-subsequences": """
def numDistinct(s, t):
    m, n = len(s), len(t)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = 1
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i - 1][j]
            if s[i - 1] == t[j - 1]:
                dp[i][j] += dp[i - 1][j - 1]
    return dp[m][n]
""",

"best-time-to-buy-and-sell-stock-iii": """
def maxProfit(prices):
    if not prices:
        return 0
    buy1 = buy2 = float('-inf')
    sell1 = sell2 = 0
    for p in prices:
        buy1 = max(buy1, -p)
        sell1 = max(sell1, buy1 + p)
        buy2 = max(buy2, sell1 - p)
        sell2 = max(sell2, buy2 + p)
    return sell2
""",

"3sum-closest": """
def threeSumClosest(nums, target):
    nums = sorted(nums)
    n = len(nums)
    best = nums[0] + nums[1] + nums[2]
    for i in range(n - 2):
        l, r = i + 1, n - 1
        while l < r:
            total = nums[i] + nums[l] + nums[r]
            if abs(total - target) < abs(best - target):
                best = total
            if total < target:
                l += 1
            elif total > target:
                r -= 1
            else:
                return total
    return best
""",

"divide-two-integers": """
def divide(dividend, divisor):
    INT_MAX, INT_MIN = 2**31 - 1, -2**31
    if dividend == INT_MIN and divisor == -1:
        return INT_MAX
    negative = (dividend < 0) != (divisor < 0)
    a, b = abs(dividend), abs(divisor)
    result = 0
    while a >= b:
        temp, multiple = b, 1
        while a >= (temp << 1):
            temp <<= 1
            multiple <<= 1
        a -= temp
        result += multiple
    if negative:
        result = -result
    return max(INT_MIN, min(INT_MAX, result))
""",

"palindrome-partitioning-ii": """
def minCut(s):
    n = len(s)
    is_pal = [[False] * n for _ in range(n)]
    for i in range(n):
        is_pal[i][i] = True
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            if s[i] == s[j] and (length == 2 or is_pal[i + 1][j - 1]):
                is_pal[i][j] = True
    cuts = [0] * n
    for i in range(n):
        if is_pal[0][i]:
            cuts[i] = 0
        else:
            cuts[i] = min(cuts[j] + 1 for j in range(i) if is_pal[j + 1][i])
    return cuts[n - 1]
""",

"candy": """
def candy(ratings):
    n = len(ratings)
    candies = [1] * n
    for i in range(1, n):
        if ratings[i] > ratings[i - 1]:
            candies[i] = candies[i - 1] + 1
    for i in range(n - 2, -1, -1):
        if ratings[i] > ratings[i + 1]:
            candies[i] = max(candies[i], candies[i + 1] + 1)
    return sum(candies)
""",

"max-points-on-a-line": """
from math import gcd
def maxPoints(points):
    n = len(points)
    if n <= 2:
        return n
    best = 1
    for i in range(n):
        slopes = {}
        for j in range(n):
            if i == j:
                continue
            dx = points[j][0] - points[i][0]
            dy = points[j][1] - points[i][1]
            if dx == 0:
                key = ('inf',)
            else:
                g = gcd(dx, dy)
                dx //= g
                dy //= g
                if dx < 0:
                    dx, dy = -dx, -dy
                key = (dx, dy)
            slopes[key] = slopes.get(key, 0) + 1
        if slopes:
            best = max(best, max(slopes.values()) + 1)
    return best
""",

"roman-to-integer": """
def romanToInt(s):
    vals = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
    total = 0
    for i in range(len(s)):
        if i + 1 < len(s) and vals[s[i]] < vals[s[i + 1]]:
            total -= vals[s[i]]
        else:
            total += vals[s[i]]
    return total
""",

"find-minimum-in-rotated-sorted-array-ii": """
def findMin(nums):
    l, r = 0, len(nums) - 1
    while l < r:
        mid = (l + r) // 2
        if nums[mid] > nums[r]:
            l = mid + 1
        elif nums[mid] < nums[r]:
            r = mid
        else:
            r -= 1
    return nums[l]
""",

"dungeon-game": """
def calculateMinimumHP(dungeon):
    m, n = len(dungeon), len(dungeon[0])
    dp = [[float('inf')] * (n + 1) for _ in range(m + 1)]
    dp[m][n - 1] = dp[m - 1][n] = 1
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            need = min(dp[i + 1][j], dp[i][j + 1]) - dungeon[i][j]
            dp[i][j] = max(1, need)
    return dp[0][0]
""",

"search-in-rotated-sorted-array": """
def search(nums, target):
    l, r = 0, len(nums) - 1
    while l <= r:
        mid = (l + r) // 2
        if nums[mid] == target:
            return mid
        if nums[l] <= nums[mid]:
            if nums[l] <= target < nums[mid]:
                r = mid - 1
            else:
                l = mid + 1
        else:
            if nums[mid] < target <= nums[r]:
                l = mid + 1
            else:
                r = mid - 1
    return -1
""",

"best-time-to-buy-and-sell-stock-iv": """
def maxProfit(k, prices):
    n = len(prices)
    if n == 0 or k == 0:
        return 0
    if k >= n // 2:
        return sum(max(prices[i + 1] - prices[i], 0) for i in range(n - 1))
    buy = [float('-inf')] * (k + 1)
    sell = [0] * (k + 1)
    for p in prices:
        for i in range(1, k + 1):
            buy[i] = max(buy[i], sell[i - 1] - p)
            sell[i] = max(sell[i], buy[i] + p)
    return sell[k]
""",

"shortest-palindrome": """
def shortestPalindrome(s):
    if not s:
        return s
    rev = s[::-1]
    combined = s + '#' + rev
    n = len(combined)
    lps = [0] * n
    for i in range(1, n):
        j = lps[i - 1]
        while j > 0 and combined[i] != combined[j]:
            j = lps[j - 1]
        if combined[i] == combined[j]:
            j += 1
        lps[i] = j
    overlap = lps[-1]
    return rev[:len(s) - overlap] + s
""",

"longest-common-prefix": """
def longestCommonPrefix(strs):
    if not strs:
        return ""
    prefix = strs[0]
    for s in strs[1:]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix
""",

"find-first-and-last-position-of-element-in-sorted-array": """
import bisect
def searchRange(nums, target):
    l = bisect.bisect_left(nums, target)
    if l == len(nums) or nums[l] != target:
        return [-1, -1]
    r = bisect.bisect_right(nums, target) - 1
    return [l, r]
""",

"valid-sudoku": """
def isValidSudoku(board):
    rows = [set() for _ in range(9)]
    cols = [set() for _ in range(9)]
    boxes = [set() for _ in range(9)]
    for i in range(9):
        for j in range(9):
            v = board[i][j]
            if v == '.':
                continue
            b = (i // 3) * 3 + j // 3
            if v in rows[i] or v in cols[j] or v in boxes[b]:
                return False
            rows[i].add(v); cols[j].add(v); boxes[b].add(v)
    return True
""",

"remove-duplicates-from-sorted-array": """
def removeDuplicates(nums):
    if not nums:
        return 0
    k = 1
    for i in range(1, len(nums)):
        if nums[i] != nums[k - 1]:
            nums[k] = nums[i]
            k += 1
    return k
""",

"count-and-say": """
def countAndSay(n):
    result = "1"
    for _ in range(n - 1):
        next_result = []
        i = 0
        while i < len(result):
            j = i
            while j < len(result) and result[j] == result[i]:
                j += 1
            next_result.append(str(j - i))
            next_result.append(result[i])
            i = j
        result = ''.join(next_result)
    return result
""",

"contains-duplicate-iii": """
def containsNearbyAlmostDuplicate(nums, indexDiff, valueDiff):
    if valueDiff < 0 or indexDiff <= 0:
        return False
    buckets = {}
    w = valueDiff + 1
    for i, num in enumerate(nums):
        bucket_id = num // w
        if bucket_id in buckets:
            return True
        if bucket_id - 1 in buckets and abs(num - buckets[bucket_id - 1]) <= valueDiff:
            return True
        if bucket_id + 1 in buckets and abs(num - buckets[bucket_id + 1]) <= valueDiff:
            return True
        buckets[bucket_id] = num
        if i >= indexDiff:
            del_bucket = nums[i - indexDiff] // w
            if del_bucket in buckets:
                del buckets[del_bucket]
    return False
""",

"remove-element": """
def removeElement(nums, val):
    k = 0
    for i in range(len(nums)):
        if nums[i] != val:
            nums[k] = nums[i]
            k += 1
    return k
""",

"multiply-strings": """
def multiply(num1, num2):
    if num1 == "0" or num2 == "0":
        return "0"
    m, n = len(num1), len(num2)
    result = [0] * (m + n)
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            mul = int(num1[i]) * int(num2[j])
            p1, p2 = i + j, i + j + 1
            total = mul + result[p2]
            result[p2] = total % 10
            result[p1] += total // 10
    result_str = ''.join(map(str, result)).lstrip('0')
    return result_str if result_str else "0"
""",
}

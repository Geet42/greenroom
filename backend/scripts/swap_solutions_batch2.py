"""
Batch 2 of hand-authored reference solutions (see swap_solutions.py for the
rationale) — for the 109 replacement candidates found in the second,
deeper swap pass (up to the 5 already covered by swap_solutions.py's
original 41, which are reused automatically since both dicts get merged).
"""
from __future__ import annotations

SOLUTIONS_2: dict[str, str] = {

"basic-calculator": """
def calculate(s):
    stack = []
    result = 0
    number = 0
    sign = 1
    for c in s:
        if c.isdigit():
            number = number * 10 + int(c)
        elif c == '+':
            result += sign * number
            number = 0
            sign = 1
        elif c == '-':
            result += sign * number
            number = 0
            sign = -1
        elif c == '(':
            stack.append(result)
            stack.append(sign)
            result = 0
            sign = 1
        elif c == ')':
            result += sign * number
            number = 0
            result *= stack.pop()
            result += stack.pop()
    result += sign * number
    return result
""",

"jump-game-ii": """
def jump(nums):
    n = len(nums)
    jumps = 0
    cur_end = 0
    farthest = 0
    for i in range(n - 1):
        farthest = max(farthest, i + nums[i])
        if i == cur_end:
            jumps += 1
            cur_end = farthest
    return jumps
""",

"powx-n": """
def myPow(x, n):
    if n < 0:
        x = 1 / x
        n = -n
    result = 1.0
    while n:
        if n & 1:
            result *= x
        x *= x
        n >>= 1
    return result
""",

"find-the-index-of-the-first-occurrence-in-a-string": """
def strStr(haystack, needle):
    if needle == "":
        return 0
    n, m = len(haystack), len(needle)
    for i in range(n - m + 1):
        if haystack[i:i + m] == needle:
            return i
    return -1
""",

"number-of-digit-one": """
def countDigitOne(n):
    if n < 1:
        return 0
    count = 0
    i = 1
    while i <= n:
        divider = i * 10
        count += (n // divider) * i + min(max(n % divider - i + 1, 0), i)
        i *= 10
    return count
""",

"sliding-window-maximum": """
from collections import deque
def maxSlidingWindow(nums, k):
    dq = deque()
    result = []
    for i, num in enumerate(nums):
        while dq and nums[dq[-1]] <= num:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - k:
            dq.popleft()
        if i >= k - 1:
            result.append(nums[dq[0]])
    return result
""",

"integer-to-english-words": """
def numberToWords(num):
    if num == 0:
        return "Zero"
    below20 = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
               "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
               "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    thousands = ["", "Thousand", "Million", "Billion"]

    def helper(n):
        if n == 0:
            return ""
        if n < 20:
            return below20[n] + " "
        if n < 100:
            return tens[n // 10] + " " + helper(n % 10)
        return below20[n // 100] + " Hundred " + helper(n % 100)

    res = ""
    i = 0
    while num > 0:
        if num % 1000 != 0:
            res = helper(num % 1000) + thousands[i] + " " + res
        num //= 1000
        i += 1
    return res.strip()
""",

"search-insert-position": """
import bisect
def searchInsert(nums, target):
    return bisect.bisect_left(nums, target)
""",

"length-of-last-word": """
def lengthOfLastWord(s):
    parts = s.split()
    return len(parts[-1]) if parts else 0
""",

"plus-one": """
def plusOne(digits):
    digits = digits[:]
    for i in range(len(digits) - 1, -1, -1):
        if digits[i] < 9:
            digits[i] += 1
            return digits
        digits[i] = 0
    return [1] + digits
""",

"add-binary": """
def addBinary(a, b):
    return bin(int(a, 2) + int(b, 2))[2:]
""",

"sqrtx": """
def mySqrt(x):
    if x < 2:
        return x
    lo, hi = 1, x // 2
    while lo <= hi:
        mid = (lo + hi) // 2
        if mid * mid == x:
            return mid
        if mid * mid < x:
            lo = mid + 1
        else:
            hi = mid - 1
    return hi
""",

"climbing-stairs": """
def climbStairs(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a
""",

"best-time-to-buy-and-sell-stock": """
def maxProfit(prices):
    min_price = float('inf')
    best = 0
    for p in prices:
        min_price = min(min_price, p)
        best = max(best, p - min_price)
    return best
""",

"valid-palindrome": """
def isPalindrome(s):
    filtered = [c.lower() for c in s if c.isalnum()]
    return filtered == filtered[::-1]
""",

"single-number": """
def singleNumber(nums):
    result = 0
    for n in nums:
        result ^= n
    return result
""",

"jump-game": """
def canJump(nums):
    reach = 0
    for i, n in enumerate(nums):
        if i > reach:
            return False
        reach = max(reach, i + n)
    return True
""",

"insert-interval": """
def insert(intervals, newInterval):
    result = []
    i = 0
    n = len(intervals)
    while i < n and intervals[i][1] < newInterval[0]:
        result.append(intervals[i])
        i += 1
    start, end = newInterval[0], newInterval[1]
    while i < n and intervals[i][0] <= end:
        start = min(start, intervals[i][0])
        end = max(end, intervals[i][1])
        i += 1
    result.append([start, end])
    while i < n:
        result.append(intervals[i])
        i += 1
    return result
""",

"spiral-matrix-ii": """
def generateMatrix(n):
    matrix = [[0] * n for _ in range(n)]
    top, bottom, left, right = 0, n - 1, 0, n - 1
    num = 1
    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            matrix[top][c] = num; num += 1
        top += 1
        for r in range(top, bottom + 1):
            matrix[r][right] = num; num += 1
        right -= 1
        if top <= bottom:
            for c in range(right, left - 1, -1):
                matrix[bottom][c] = num; num += 1
            bottom -= 1
        if left <= right:
            for r in range(bottom, top - 1, -1):
                matrix[r][left] = num; num += 1
            left += 1
    return matrix
""",

"unique-paths": """
def uniquePaths(m, n):
    dp = [1] * n
    for _ in range(1, m):
        for j in range(1, n):
            dp[j] += dp[j - 1]
    return dp[-1]
""",

"unique-paths-ii": """
def uniquePathsWithObstacles(obstacleGrid):
    m, n = len(obstacleGrid), len(obstacleGrid[0])
    dp = [0] * n
    dp[0] = 1
    for i in range(m):
        for j in range(n):
            if obstacleGrid[i][j] == 1:
                dp[j] = 0
            elif j > 0:
                dp[j] += dp[j - 1]
    return dp[-1]
""",

"minimum-path-sum": """
def minPathSum(grid):
    m, n = len(grid), len(grid[0])
    dp = [[0] * n for _ in range(m)]
    dp[0][0] = grid[0][0]
    for j in range(1, n):
        dp[0][j] = dp[0][j - 1] + grid[0][j]
    for i in range(1, m):
        dp[i][0] = dp[i - 1][0] + grid[i][0]
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = min(dp[i - 1][j], dp[i][j - 1]) + grid[i][j]
    return dp[-1][-1]
""",

"burst-balloons": """
def maxCoins(nums):
    balloons = [1] + nums + [1]
    n = len(balloons)
    dp = [[0] * n for _ in range(n)]
    for length in range(2, n):
        for left in range(0, n - length):
            right = left + length
            for k in range(left + 1, right):
                dp[left][right] = max(
                    dp[left][right],
                    dp[left][k] + dp[k][right] + balloons[left] * balloons[k] * balloons[right],
                )
    return dp[0][n - 1]
""",

"create-maximum-number": """
def maxNumber(nums1, nums2, k):
    def prep(nums, length):
        stack = []
        drop = len(nums) - length
        for x in nums:
            while stack and drop and stack[-1] < x:
                stack.pop()
                drop -= 1
            stack.append(x)
        return stack[:length]

    def merge(a, b):
        return [max(a, b).pop(0) for _ in range(len(a) + len(b))]

    result = [0] * k
    for i in range(max(0, k - len(nums2)), min(k, len(nums1)) + 1):
        candidate = merge(prep(nums1, i), prep(nums2, k - i))
        if candidate > result:
            result = candidate
    return result
""",

"simplify-path": """
def simplifyPath(path):
    parts = path.split('/')
    stack = []
    for p in parts:
        if p == '' or p == '.':
            continue
        if p == '..':
            if stack:
                stack.pop()
        else:
            stack.append(p)
    return '/' + '/'.join(stack)
""",

"edit-distance": """
def minDistance(word1, word2):
    m, n = len(word1), len(word2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i - 1] == word2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]
""",

"count-of-range-sum": """
def countRangeSum(nums, lower, upper):
    prefix = [0]
    for n in nums:
        prefix.append(prefix[-1] + n)

    def merge_sort(lo, hi):
        if hi - lo <= 1:
            return 0
        mid = (lo + hi) // 2
        count = merge_sort(lo, mid) + merge_sort(mid, hi)
        j = k = mid
        for i in range(lo, mid):
            while j < hi and prefix[j] - prefix[i] < lower:
                j += 1
            while k < hi and prefix[k] - prefix[i] <= upper:
                k += 1
            count += k - j
        prefix[lo:hi] = sorted(prefix[lo:hi])
        return count

    return merge_sort(0, len(prefix))
""",

"search-a-2d-matrix": """
def searchMatrix(matrix, target):
    if not matrix or not matrix[0]:
        return False
    m, n = len(matrix), len(matrix[0])
    lo, hi = 0, m * n - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        val = matrix[mid // n][mid % n]
        if val == target:
            return True
        if val < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return False
""",

"longest-increasing-path-in-a-matrix": """
def longestIncreasingPath(matrix):
    if not matrix or not matrix[0]:
        return 0
    m, n = len(matrix), len(matrix[0])
    memo = [[0] * n for _ in range(m)]

    def dfs(i, j):
        if memo[i][j]:
            return memo[i][j]
        best = 1
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ni, nj = i + di, j + dj
            if 0 <= ni < m and 0 <= nj < n and matrix[ni][nj] > matrix[i][j]:
                best = max(best, 1 + dfs(ni, nj))
        memo[i][j] = best
        return best

    return max(dfs(i, j) for i in range(m) for j in range(n))
""",

"word-search": """
def exist(board, word):
    m, n = len(board), len(board[0])

    def dfs(i, j, k):
        if k == len(word):
            return True
        if i < 0 or i >= m or j < 0 or j >= n or board[i][j] != word[k]:
            return False
        tmp = board[i][j]
        board[i][j] = '#'
        found = (dfs(i + 1, j, k + 1) or dfs(i - 1, j, k + 1) or
                 dfs(i, j + 1, k + 1) or dfs(i, j - 1, k + 1))
        board[i][j] = tmp
        return found

    for i in range(m):
        for j in range(n):
            if dfs(i, j, 0):
                return True
    return False
""",

"remove-duplicates-from-sorted-array-ii": """
def removeDuplicates(nums):
    k = 0
    for num in nums:
        if k < 2 or num != nums[k - 2]:
            nums[k] = num
            k += 1
    return k
""",

"patching-array": """
def minPatches(nums, n):
    miss = 1
    patches = 0
    i = 0
    while miss <= n:
        if i < len(nums) and nums[i] <= miss:
            miss += nums[i]
            i += 1
        else:
            miss += miss
            patches += 1
    return patches
""",

"search-in-rotated-sorted-array-ii": """
def search(nums, target):
    l, r = 0, len(nums) - 1
    while l <= r:
        mid = (l + r) // 2
        if nums[mid] == target:
            return True
        if nums[l] == nums[mid] == nums[r]:
            l += 1
            r -= 1
        elif nums[l] <= nums[mid]:
            if nums[l] <= target < nums[mid]:
                r = mid - 1
            else:
                l = mid + 1
        else:
            if nums[mid] < target <= nums[r]:
                l = mid + 1
            else:
                r = mid - 1
    return False
""",

"self-crossing": """
def isSelfCrossing(distance):
    n = len(distance)
    for i in range(3, n):
        if distance[i] >= distance[i - 2] and distance[i - 1] <= distance[i - 3]:
            return True
        if i >= 4 and distance[i - 1] == distance[i - 3] and distance[i] + distance[i - 4] >= distance[i - 2]:
            return True
        if i >= 5 and distance[i - 2] >= distance[i - 4] and distance[i] + distance[i - 4] >= distance[i - 2] and \\
           distance[i - 1] <= distance[i - 3] and distance[i - 3] <= distance[i - 5] + distance[i - 1]:
            return True
    return False
""",

"decode-ways": """
def numDecodings(s):
    if not s or s[0] == '0':
        return 0
    n = len(s)
    dp = [0] * (n + 1)
    dp[0], dp[1] = 1, 1
    for i in range(2, n + 1):
        one = int(s[i - 1:i])
        two = int(s[i - 2:i])
        if one >= 1:
            dp[i] += dp[i - 1]
        if 10 <= two <= 26:
            dp[i] += dp[i - 2]
    return dp[n]
""",

"unique-binary-search-trees": """
def numTrees(n):
    dp = [1] * (n + 1)
    for nodes in range(2, n + 1):
        total = 0
        for root in range(1, nodes + 1):
            total += dp[root - 1] * dp[nodes - root]
        dp[nodes] = total
    return dp[n]
""",

"interleaving-string": """
def isInterleave(s1, s2, s3):
    m, n = len(s1), len(s2)
    if m + n != len(s3):
        return False
    dp = [[False] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = True
    for i in range(1, m + 1):
        dp[i][0] = dp[i - 1][0] and s1[i - 1] == s3[i - 1]
    for j in range(1, n + 1):
        dp[0][j] = dp[0][j - 1] and s2[j - 1] == s3[j - 1]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = (dp[i - 1][j] and s1[i - 1] == s3[i + j - 1]) or \\
                       (dp[i][j - 1] and s2[j - 1] == s3[i + j - 1])
    return dp[m][n]
""",

"best-time-to-buy-and-sell-stock-ii": """
def maxProfit(prices):
    profit = 0
    for i in range(1, len(prices)):
        if prices[i] > prices[i - 1]:
            profit += prices[i] - prices[i - 1]
    return profit
""",

"russian-doll-envelopes": """
import bisect
def maxEnvelopes(envelopes):
    envelopes.sort(key=lambda e: (e[0], -e[1]))
    tails = []
    for _, h in envelopes:
        idx = bisect.bisect_left(tails, h)
        if idx == len(tails):
            tails.append(h)
        else:
            tails[idx] = h
    return len(tails)
""",

"longest-consecutive-sequence": """
def longestConsecutive(nums):
    numset = set(nums)
    best = 0
    for n in numset:
        if n - 1 not in numset:
            length = 1
            while n + length in numset:
                length += 1
            best = max(best, length)
    return best
""",

"max-sum-of-rectangle-no-larger-than-k": """
import bisect
def maxSumSubmatrix(matrix, k):
    m, n = len(matrix), len(matrix[0])
    best = float('-inf')
    for left in range(n):
        row_sums = [0] * m
        for right in range(left, n):
            for i in range(m):
                row_sums[i] += matrix[i][right]
            prefix_sorted = [0]
            cur = 0
            for s in row_sums:
                cur += s
                idx = bisect.bisect_left(prefix_sorted, cur - k)
                if idx < len(prefix_sorted):
                    best = max(best, cur - prefix_sorted[idx])
                bisect.insort(prefix_sorted, cur)
    return best
""",

"perfect-rectangle": """
def isRectangleCover(rectangles):
    area = 0
    corners = set()
    minX = minY = float('inf')
    maxX = maxY = float('-inf')
    for x1, y1, x2, y2 in rectangles:
        area += (x2 - x1) * (y2 - y1)
        minX, minY = min(minX, x1), min(minY, y1)
        maxX, maxY = max(maxX, x2), max(maxY, y2)
        for corner in [(x1, y1), (x1, y2), (x2, y1), (x2, y2)]:
            if corner in corners:
                corners.remove(corner)
            else:
                corners.add(corner)
    expected_corners = {(minX, minY), (minX, maxY), (maxX, minY), (maxX, maxY)}
    return corners == expected_corners and area == (maxX - minX) * (maxY - minY)
""",

"gas-station": """
def canCompleteCircuit(gas, cost):
    total, tank, start = 0, 0, 0
    for i in range(len(gas)):
        diff = gas[i] - cost[i]
        total += diff
        tank += diff
        if tank < 0:
            start = i + 1
            tank = 0
    return start if total >= 0 else -1
""",

"single-number-ii": """
def singleNumber(nums):
    ones, twos = 0, 0
    for n in nums:
        ones = (ones ^ n) & ~twos
        twos = (twos ^ n) & ~ones
    return ones
""",

"frog-jump": """
def canCross(stones):
    if stones[1] != 1:
        return False
    stone_set = set(stones)
    visited = set()
    def dfs(pos, k):
        if pos == stones[-1]:
            return True
        if (pos, k) in visited:
            return False
        visited.add((pos, k))
        for step in (k - 1, k, k + 1):
            if step > 0 and (pos + step) in stone_set:
                if dfs(pos + step, step):
                    return True
        return False
    return dfs(1, 1)
""",

"trapping-rain-water-ii": """
import heapq
def trapRainWater(heightMap):
    if not heightMap or not heightMap[0]:
        return 0
    m, n = len(heightMap), len(heightMap[0])
    visited = [[False] * n for _ in range(m)]
    heap = []
    for i in range(m):
        for j in range(n):
            if i == 0 or i == m - 1 or j == 0 or j == n - 1:
                heapq.heappush(heap, (heightMap[i][j], i, j))
                visited[i][j] = True
    water = 0
    while heap:
        height, i, j = heapq.heappop(heap)
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ni, nj = i + di, j + dj
            if 0 <= ni < m and 0 <= nj < n and not visited[ni][nj]:
                visited[ni][nj] = True
                water += max(0, height - heightMap[ni][nj])
                heapq.heappush(heap, (max(height, heightMap[ni][nj]), ni, nj))
    return water
""",

"evaluate-reverse-polish-notation": """
def evalRPN(tokens):
    stack = []
    ops = {'+', '-', '*', '/'}
    for t in tokens:
        if t in ops:
            b = stack.pop()
            a = stack.pop()
            if t == '+':
                stack.append(a + b)
            elif t == '-':
                stack.append(a - b)
            elif t == '*':
                stack.append(a * b)
            else:
                stack.append(int(a / b))
        else:
            stack.append(int(t))
    return stack[0]
""",

"reverse-words-in-a-string": """
def reverseWords(s):
    return ' '.join(reversed(s.split()))
""",

"maximum-product-subarray": """
def maxProduct(nums):
    result = nums[0]
    cur_max = cur_min = nums[0]
    for n in nums[1:]:
        candidates = (n, cur_max * n, cur_min * n)
        cur_max, cur_min = max(candidates), min(candidates)
        result = max(result, cur_max)
    return result
""",

"find-minimum-in-rotated-sorted-array": """
def findMin(nums):
    l, r = 0, len(nums) - 1
    while l < r:
        mid = (l + r) // 2
        if nums[mid] > nums[r]:
            l = mid + 1
        else:
            r = mid
    return nums[l]
""",

"find-peak-element": """
def findPeakElement(nums):
    l, r = 0, len(nums) - 1
    while l < r:
        mid = (l + r) // 2
        if nums[mid] > nums[mid + 1]:
            r = mid
        else:
            l = mid + 1
    return l
""",

"maximum-gap": """
def maximumGap(nums):
    if len(nums) < 2:
        return 0
    nums = sorted(nums)
    return max(nums[i + 1] - nums[i] for i in range(len(nums) - 1))
""",

"split-array-largest-sum": """
def splitArray(nums, k):
    def can_split(mid):
        pieces, cur = 1, 0
        for n in nums:
            if cur + n > mid:
                pieces += 1
                cur = n
                if pieces > k:
                    return False
            else:
                cur += n
        return True

    lo, hi = max(nums), sum(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if can_split(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo
""",

"strong-password-checker": """
def strongPasswordChecker(password):
    n = len(password)
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    missing_types = 3 - (has_lower + has_upper + has_digit)

    change = 0
    one = two = 0
    i = 2
    while i < n:
        if password[i] == password[i - 1] == password[i - 2]:
            length = 2
            while i < n and password[i] == password[i - 1]:
                length += 1
                i += 1
            change += length // 3
            if length % 3 == 0:
                one += 1
            elif length % 3 == 1:
                two += 1
        else:
            i += 1

    if n < 6:
        return max(missing_types, 6 - n)
    if n <= 20:
        return max(missing_types, change)

    delete = n - 20
    change -= min(delete, one)
    change -= min(max(delete - one, 0), two * 2) // 2
    change -= max(delete - one - 2 * two, 0) // 3
    return delete + max(missing_types, change)
""",

"k-th-smallest-in-lexicographical-order": """
def findKthNumber(n, k):
    def count_steps(n, prefix1, prefix2):
        steps = 0
        while prefix1 <= n:
            steps += min(n + 1, prefix2) - prefix1
            prefix1 *= 10
            prefix2 *= 10
        return steps

    cur = 1
    k -= 1
    while k > 0:
        steps = count_steps(n, cur, cur + 1)
        if steps <= k:
            cur += 1
            k -= steps
        else:
            cur *= 10
            k -= 1
    return cur
""",

"compare-version-numbers": """
def compareVersion(version1, version2):
    v1 = version1.split('.')
    v2 = version2.split('.')
    n = max(len(v1), len(v2))
    for i in range(n):
        x1 = int(v1[i]) if i < len(v1) else 0
        x2 = int(v2[i]) if i < len(v2) else 0
        if x1 != x2:
            return 1 if x1 > x2 else -1
    return 0
""",

"arithmetic-slices-ii-subsequence": """
def numberOfArithmeticSlices(nums):
    n = len(nums)
    total = 0
    dp = [dict() for _ in range(n)]
    for i in range(n):
        for j in range(i):
            diff = nums[i] - nums[j]
            cnt = dp[j].get(diff, 0)
            total += cnt
            dp[i][diff] = dp[i].get(diff, 0) + cnt + 1
    return total
""",

"fraction-to-recurring-decimal": """
def fractionToDecimal(numerator, denominator):
    if numerator == 0:
        return "0"
    result = []
    if (numerator < 0) != (denominator < 0):
        result.append('-')
    numerator, denominator = abs(numerator), abs(denominator)
    result.append(str(numerator // denominator))
    remainder = numerator % denominator
    if remainder == 0:
        return ''.join(result)
    result.append('.')
    seen = {}
    while remainder != 0:
        if remainder in seen:
            result.insert(seen[remainder], '(')
            result.append(')')
            break
        seen[remainder] = len(result)
        remainder *= 10
        result.append(str(remainder // denominator))
        remainder %= denominator
    return ''.join(result)
""",

"poor-pigs": """
import math
def poorPigs(buckets, minutesToDie, minutesToTest):
    rounds = minutesToTest // minutesToDie
    return math.ceil(math.log(buckets) / math.log(rounds + 1))
""",

"two-sum-ii-input-array-is-sorted": """
def twoSum(numbers, target):
    l, r = 0, len(numbers) - 1
    while l < r:
        s = numbers[l] + numbers[r]
        if s == target:
            return [l + 1, r + 1]
        if s < target:
            l += 1
        else:
            r -= 1
    return []
""",

"count-the-repetitions": """
def getMaxRepetitions(s1, n1, s2, n2):
    if not s1 or not s2:
        return 0
    len2 = len(s2)
    j = 0
    count_s1 = 0
    match_counts = []
    j_positions = {}
    while count_s1 < n1:
        if j in j_positions:
            prev_count_s1 = j_positions[j]
            prev_match_count = match_counts[prev_count_s1]
            cycle_len = count_s1 - prev_count_s1
            cycle_match = match_counts[-1] - prev_match_count
            remaining = n1 - count_s1
            cycles = remaining // cycle_len
            count_s1 += cycles * cycle_len
            total_match = cycle_match * cycles + prev_match_count
            for _ in range(n1 - count_s1):
                for c in s1:
                    if c == s2[j]:
                        j += 1
                        if j == len2:
                            j = 0
                            total_match += 1
                count_s1 += 1
            return total_match // n2
        j_positions[j] = count_s1
        match_count = match_counts[-1] if match_counts else 0
        for c in s1:
            if c == s2[j]:
                j += 1
                if j == len2:
                    j = 0
                    match_count += 1
        match_counts.append(match_count)
        count_s1 += 1
    return match_counts[-1] // n2
""",

"largest-palindrome-product": """
def largestPalindrome(n):
    if n == 1:
        return 9
    upper = 10**n - 1
    lower = 10**(n - 1)
    for a in range(upper, lower - 1, -1):
        b = a
        candidate = int(str(a) + str(a)[::-1])
        found = False
        b = upper
        while b * upper >= candidate and b >= lower:
            if candidate % b == 0:
                factor = candidate // b
                if lower <= factor <= upper:
                    return candidate % 1337
            b -= 1
    return 9
""",

"factorial-trailing-zeroes": """
def trailingZeroes(n):
    count = 0
    power = 5
    while power <= n:
        count += n // power
        power *= 5
    return count
""",

"sliding-window-median": """
import bisect
def medianSlidingWindow(nums, k):
    window = sorted(nums[:k])
    result = []
    for i in range(k, len(nums) + 1):
        if k % 2 == 1:
            result.append(float(window[k // 2]))
        else:
            result.append((window[k // 2 - 1] + window[k // 2]) / 2.0)
        if i == len(nums):
            break
        out = nums[i - k]
        idx = bisect.bisect_left(window, out)
        window.pop(idx)
        bisect.insort(window, nums[i])
    return result
""",

"smallest-good-base": """
def smallestGoodBase(n):
    num = int(n)
    for m in range(num.bit_length(), 1, -1):
        k = int(num ** (1.0 / (m - 1)))
        if k < 2:
            continue
        total = 0
        cur = 1
        for _ in range(m):
            total += cur
            cur *= k
        if total == num:
            return str(k)
    return str(num - 1)
""",

"zuma-game": """
def findMinStep(board, hand):
    def remove_consecutive(s):
        changed = True
        while changed:
            changed = False
            i = 0
            while i < len(s):
                j = i
                while j < len(s) and s[j] == s[i]:
                    j += 1
                if j - i >= 3:
                    s = s[:i] + s[j:]
                    changed = True
                    break
                i = j
        return s

    from functools import lru_cache
    best = [float('inf')]

    def backtrack(board, hand, used):
        if not board:
            best[0] = min(best[0], used)
            return
        if used >= best[0]:
            return
        seen = set()
        for i in range(len(hand)):
            if hand[i] in seen:
                continue
            seen.add(hand[i])
            for j in range(len(board) + 1):
                if j > 0 and board[j - 1] == hand[i]:
                    new_board = board[:j] + hand[i] + board[j:]
                    new_board = remove_consecutive(new_board)
                    new_hand = hand[:i] + hand[i + 1:]
                    backtrack(new_board, new_hand, used + 1)
                elif j < len(board) and board[j] == hand[i]:
                    new_board = board[:j] + hand[i] + board[j:]
                    new_board = remove_consecutive(new_board)
                    new_hand = hand[:i] + hand[i + 1:]
                    backtrack(new_board, new_hand, used + 1)

    backtrack(board, hand, 0)
    return best[0] if best[0] != float('inf') else -1
""",

"reverse-pairs": """
def reversePairs(nums):
    def merge_sort(arr):
        if len(arr) <= 1:
            return arr, 0
        mid = len(arr) // 2
        left, cl = merge_sort(arr[:mid])
        right, cr = merge_sort(arr[mid:])
        count = cl + cr
        j = 0
        for i in range(len(left)):
            while j < len(right) and left[i] > 2 * right[j]:
                j += 1
            count += j
        merged = []
        i = j = 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                merged.append(left[i]); i += 1
            else:
                merged.append(right[j]); j += 1
        merged.extend(left[i:])
        merged.extend(right[j:])
        return merged, count

    _, total = merge_sort(nums)
    return total
""",

"ipo": """
import heapq
def findMaximizedCapital(k, w, profits, capital):
    projects = sorted(zip(capital, profits))
    max_heap = []
    i = 0
    n = len(projects)
    for _ in range(k):
        while i < n and projects[i][0] <= w:
            heapq.heappush(max_heap, -projects[i][1])
            i += 1
        if not max_heap:
            break
        w += -heapq.heappop(max_heap)
    return w
""",

"largest-number": """
from functools import cmp_to_key
def largestNumber(nums):
    strs = [str(n) for n in nums]
    strs.sort(key=cmp_to_key(lambda a, b: (a + b > b + a) - (a + b < b + a)), reverse=True)
    result = ''.join(strs).lstrip('0')
    return result if result else '0'
""",

"freedom-trail": """
def findRotateSteps(ring, key):
    n = len(ring)
    pos = {}
    for i, c in enumerate(ring):
        pos.setdefault(c, []).append(i)

    from functools import lru_cache

    @lru_cache(maxsize=None)
    def dp(cur, k):
        if k == len(key):
            return 0
        best = float('inf')
        for nxt in pos[key[k]]:
            diff = abs(cur - nxt)
            steps = min(diff, n - diff)
            best = min(best, steps + 1 + dp(nxt, k + 1))
        return best

    return dp(0, 0)
""",

"super-washing-machines": """
def findMinMoves(machines):
    total = sum(machines)
    n = len(machines)
    if total % n != 0:
        return -1
    target = total // n
    max_moves = 0
    running_sum = 0
    for m in machines:
        diff = m - target
        running_sum += diff
        max_moves = max(max_moves, abs(running_sum), diff)
    return max_moves
""",

"excel-sheet-column-title": """
def convertToTitle(columnNumber):
    result = []
    while columnNumber > 0:
        columnNumber -= 1
        result.append(chr(65 + columnNumber % 26))
        columnNumber //= 26
    return ''.join(reversed(result))
""",

"remove-boxes": """
def removeBoxes(boxes):
    from functools import lru_cache
    n = len(boxes)

    @lru_cache(maxsize=None)
    def dp(i, j, k):
        if i > j:
            return 0
        while i < j and boxes[j] == boxes[j - 1]:
            j -= 1
            k += 1
        res = dp(i, j - 1, 0) + (k + 1) * (k + 1)
        for m in range(i, j):
            if boxes[m] == boxes[j]:
                res = max(res, dp(i, m, k + 1) + dp(m + 1, j - 1, 0))
        return res

    return dp(0, n - 1, 0)
""",

"student-attendance-record-ii": """
def checkRecord(n):
    MOD = 10**9 + 7
    dp = {}
    dp[(0, 0)] = 1
    for _ in range(n):
        ndp = {}
        for (a, l), cnt in dp.items():
            for c in ('A', 'L', 'P'):
                na, nl = a, l
                if c == 'A':
                    if a == 1:
                        continue
                    na, nl = 1, 0
                elif c == 'L':
                    if l == 2:
                        continue
                    nl = l + 1
                else:
                    nl = 0
                key = (na, nl)
                ndp[key] = (ndp.get(key, 0) + cnt) % MOD
        dp = ndp
    return sum(dp.values()) % MOD
""",

"find-the-closest-palindrome": """
def nearestPalindromic(n):
    num = int(n)
    length = len(n)
    candidates = set()
    candidates.add(10**length + 1)
    candidates.add(10**(length - 1) - 1)
    prefix = int(n[:(length + 1) // 2])
    for p in (prefix - 1, prefix, prefix + 1):
        p_str = str(p)
        if length % 2 == 0:
            pal = p_str + p_str[::-1]
        else:
            pal = p_str + p_str[-2::-1]
        candidates.add(int(pal))
    candidates.discard(num)
    best = None
    for c in candidates:
        if best is None or abs(c - num) < abs(best - num) or (abs(c - num) == abs(best - num) and c < best):
            best = c
    return str(best)
""",

"majority-element": """
def majorityElement(nums):
    count = 0
    candidate = None
    for n in nums:
        if count == 0:
            candidate = n
        count += 1 if n == candidate else -1
    return candidate
""",

"excel-sheet-column-number": """
def titleToNumber(columnTitle):
    result = 0
    for c in columnTitle:
        result = result * 26 + (ord(c) - ord('A') + 1)
    return result
""",

"erect-the-fence": """
def outerTrees(trees):
    if len(trees) < 4:
        return trees
    points = sorted(map(tuple, trees))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) < 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) < 0:
            upper.pop()
        upper.append(p)
    hull = set(lower) | set(upper)
    # include collinear boundary points
    result = set(hull)
    for p in points:
        for i in range(len(lower) - 1):
            a, b = lower[i], lower[i + 1]
            if cross(a, b, p) == 0 and min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]):
                result.add(p)
        for i in range(len(upper) - 1):
            a, b = upper[i], upper[i + 1]
            if cross(a, b, p) == 0 and min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]):
                result.add(p)
    return [list(p) for p in result]
""",

"tag-validator": """
def isValid(code):
    stack = []
    i, n = 0, len(code)

    def valid_content(s):
        return True

    while i < n:
        if i > 0 and not stack:
            return False
        if code[i:i + 9] == '<![CDATA[':
            if not stack:
                return False
            j = code.find(']]>', i + 9)
            if j == -1:
                return False
            i = j + 3
        elif code[i:i + 2] == '</':
            j = code.find('>', i)
            if j == -1:
                return False
            tag = code[i + 2:j]
            if not tag or not stack or stack[-1] != tag:
                return False
            stack.pop()
            i = j + 1
            if not stack and i != n:
                return False
        elif code[i] == '<':
            j = code.find('>', i)
            if j == -1:
                return False
            tag = code[i + 1:j]
            if not (1 <= len(tag) <= 9) or not all(c.isupper() for c in tag):
                return False
            stack.append(tag)
            i = j + 1
        else:
            if not stack:
                return False
            i += 1
    return not stack and n > 0
""",

"reverse-bits": """
def reverseBits(n):
    result = 0
    for _ in range(32):
        result = (result << 1) | (n & 1)
        n >>= 1
    return result
""",

"number-of-1-bits": """
def hammingWeight(n):
    return bin(n).count('1')
""",

"non-negative-integers-without-consecutive-ones": """
def findIntegers(n):
    bits = []
    while n:
        bits.append(n & 1)
        n >>= 1
    bits = bits[::-1] or [0]
    length = len(bits)
    fib = [1, 2]
    for i in range(2, length + 1):
        fib.append(fib[-1] + fib[-2])
    result = 0
    prev_bit = 0
    for i, b in enumerate(bits):
        if b == 1:
            result += fib[length - i - 1]
            if prev_bit == 1:
                return result
        prev_bit = b
    return result + 1
""",

"k-inverse-pairs-array": """
def kInversePairs(n, k):
    MOD = 10**9 + 7
    if k > n * (n - 1) // 2:
        return 0
    dp = [1] + [0] * k
    for i in range(2, n + 1):
        new_dp = [0] * (k + 1)
        prefix = 0
        for j in range(k + 1):
            prefix = (prefix + dp[j]) % MOD
            if j - i >= 0:
                prefix = (prefix - dp[j - i]) % MOD
            new_dp[j] = prefix
        dp = new_dp
    return dp[k] % MOD
""",

"happy-number": """
def isHappy(n):
    seen = set()
    while n != 1 and n not in seen:
        seen.add(n)
        n = sum(int(d) ** 2 for d in str(n))
    return n == 1
""",

"course-schedule-iii": """
import heapq
def scheduleCourse(courses):
    courses.sort(key=lambda c: c[1])
    heap = []
    time = 0
    for duration, deadline in courses:
        heapq.heappush(heap, -duration)
        time += duration
        if time > deadline:
            time += heapq.heappop(heap)
    return len(heap)
""",

"decode-ways-ii": """
def numDecodings(s):
    MOD = 10**9 + 7
    n = len(s)
    dp = [0] * (n + 1)
    dp[0] = 1
    for i in range(1, n + 1):
        c = s[i - 1]
        if c == '*':
            dp[i] = 9 * dp[i - 1]
        elif c != '0':
            dp[i] = dp[i - 1]
        if i >= 2:
            prev = s[i - 2]
            if prev == '*' and c == '*':
                dp[i] += 15 * dp[i - 2]
            elif prev == '*':
                if c <= '6':
                    dp[i] += 2 * dp[i - 2]
                else:
                    dp[i] += dp[i - 2]
            elif c == '*':
                if prev == '1':
                    dp[i] += 9 * dp[i - 2]
                elif prev == '2':
                    dp[i] += 6 * dp[i - 2]
            else:
                two = int(prev + c)
                if 10 <= two <= 26:
                    dp[i] += dp[i - 2]
        dp[i] %= MOD
    return dp[n] % MOD
""",

"isomorphic-strings": """
def isIsomorphic(s, t):
    map_st, map_ts = {}, {}
    for a, b in zip(s, t):
        if a in map_st and map_st[a] != b:
            return False
        if b in map_ts and map_ts[b] != a:
            return False
        map_st[a] = b
        map_ts[b] = a
    return True
""",

"contains-duplicate": """
def containsDuplicate(nums):
    return len(nums) != len(set(nums))
""",

"contains-duplicate-ii": """
def containsNearbyDuplicate(nums, k):
    last_seen = {}
    for i, n in enumerate(nums):
        if n in last_seen and i - last_seen[n] <= k:
            return True
        last_seen[n] = i
    return False
""",

"strange-printer": """
def strangePrinter(s):
    if not s:
        return 0
    n = len(s)
    dp = [[0] * n for _ in range(n)]
    for i in range(n - 1, -1, -1):
        dp[i][i] = 1
        for j in range(i + 1, n):
            dp[i][j] = dp[i][j - 1] + 1
            for k in range(i, j):
                if s[k] == s[j]:
                    dp[i][j] = min(dp[i][j], dp[i][k] + (dp[k + 1][j - 1] if k + 1 <= j - 1 else 0))
    return dp[0][n - 1]
""",

"power-of-two": """
def isPowerOfTwo(n):
    return n > 0 and (n & (n - 1)) == 0
""",

"add-digits": """
def addDigits(num):
    if num == 0:
        return 0
    return 1 + (num - 1) % 9
""",

"kth-smallest-number-in-multiplication-table": """
def findKthNumber(m, n, k):
    def count_le(x):
        total = 0
        for i in range(1, m + 1):
            total += min(x // i, n)
        return total

    lo, hi = 1, m * n
    while lo < hi:
        mid = (lo + hi) // 2
        if count_le(mid) < k:
            lo = mid + 1
        else:
            hi = mid
    return lo
""",

"24-game": """
from itertools import permutations
def judgePoint24(cards):
    def solve(nums):
        if len(nums) == 1:
            return abs(nums[0] - 24) < 1e-6
        for i in range(len(nums)):
            for j in range(len(nums)):
                if i == j:
                    continue
                rest = [nums[k] for k in range(len(nums)) if k != i and k != j]
                a, b = nums[i], nums[j]
                candidates = [a + b, a - b, a * b]
                if abs(b) > 1e-6:
                    candidates.append(a / b)
                for c in candidates:
                    if solve(rest + [c]):
                        return True
        return False
    return solve([float(c) for c in cards])
""",

"ugly-number": """
def isUgly(n):
    if n <= 0:
        return False
    for p in (2, 3, 5):
        while n % p == 0:
            n //= p
    return n == 1
""",

"redundant-connection-ii": """
def findRedundantDirectedConnection(edges):
    n = len(edges)
    parent = [0] * (n + 1)
    cand1 = cand2 = None
    for i, (u, v) in enumerate(edges):
        if parent[v] != 0:
            cand1 = [parent[v], v]
            cand2 = [u, v]
            edges[i][1] = 0
        else:
            parent[v] = u

    uf = list(range(n + 1))

    def find(x):
        while uf[x] != x:
            uf[x] = uf[uf[x]]
            x = uf[x]
        return x

    for u, v in edges:
        if v == 0:
            continue
        ru, rv = find(u), find(v)
        if ru == rv:
            if cand1:
                return cand1
            return [u, v]
        uf[ru] = rv
    return cand2
""",

"stickers-to-spell-word": """
from collections import Counter
def minStickers(stickers, target):
    from functools import lru_cache
    sticker_counters = [Counter(s) for s in stickers]

    @lru_cache(maxsize=None)
    def dp(remaining):
        if not remaining:
            return 0
        remaining_counter = Counter(remaining)
        best = float('inf')
        for sc in sticker_counters:
            if sc.get(remaining[0], 0) == 0:
                continue
            new_remaining = remaining_counter - sc
            new_remaining_str = ''.join(sorted(new_remaining.elements()))
            res = dp(new_remaining_str)
            if res != -1 and res + 1 < best:
                best = res + 1
        return best if best != float('inf') else -1

    result = dp(''.join(sorted(target)))
    return result
""",

"missing-number": """
def missingNumber(nums):
    n = len(nums)
    return n * (n + 1) // 2 - sum(nums)
""",

"maximum-sum-of-3-non-overlapping-subarrays": """
def maxSumOfThreeSubarrays(nums, k):
    n = len(nums)
    window_sum = sum(nums[:k])
    sums = [window_sum]
    for i in range(1, n - k + 1):
        window_sum += nums[i + k - 1] - nums[i - 1]
        sums.append(window_sum)

    m = len(sums)
    left = [0] * m
    best = 0
    for i in range(m):
        if sums[i] > sums[best]:
            best = i
        left[i] = best

    right = [0] * m
    best = m - 1
    for i in range(m - 1, -1, -1):
        if sums[i] >= sums[best]:
            best = i
        right[i] = best

    result = None
    best_total = -1
    for j in range(k, m - k):
        i = left[j - k]
        l = right[j + k]
        total = sums[i] + sums[j] + sums[l]
        if total > best_total:
            best_total = total
            result = [i, j, l]
    return result
""",

"word-pattern": """
def wordPattern(pattern, s):
    words = s.split()
    if len(pattern) != len(words):
        return False
    map_pw, map_wp = {}, {}
    for p, w in zip(pattern, words):
        if p in map_pw and map_pw[p] != w:
            return False
        if w in map_wp and map_wp[w] != p:
            return False
        map_pw[p] = w
        map_wp[w] = p
    return True
""",

"nim-game": """
def canWinNim(n):
    return n % 4 != 0
""",

"power-of-three": """
def isPowerOfThree(n):
    if n < 1:
        return False
    while n % 3 == 0:
        n //= 3
    return n == 1
""",

"counting-bits": """
def countBits(n):
    dp = [0] * (n + 1)
    for i in range(1, n + 1):
        dp[i] = dp[i >> 1] + (i & 1)
    return dp
""",

"power-of-four": """
def isPowerOfFour(n):
    return n > 0 and (n & (n - 1)) == 0 and (n - 1) % 3 == 0
""",

}

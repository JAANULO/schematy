def channel_x(p, pin, i, n, min_gap, base):
    k = i if p[1] >= pin[1] else n - 1 - i
    return max(p[0] + min_gap, pin[0] - base - 0.25 * k)

def height(n):
    return 0 if n[0] == "VAR" else 1 + max(height(c) for c in n[1])

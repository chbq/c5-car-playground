"""球门几何处理。

在 YOLO 检出的 goal 框基础上，做：
1. ROI 外扩（并 clamp 到图像边界，防越界）
2. 门框分割（默认 HSV+边缘融合；可切 HSV 白色阈值 / Canny 边缘 / 大津法）
3. 角点提取（按 corner_method 依次回退）：
   - hough：霍夫直线检测，横梁（最长水平线）与左右立柱（近似垂直线）求交点
   - template：3×3 模板匹配（hit-or-miss）锁横梁上沿与立柱外缘的外角
     TL = 1,2,3,4,7 黑、其余白；TR = 1,2,3,6,9 黑、其余白
   - shitomasi：Shi-Tomasi 角点检测，限制在框上半部，取最左/最右角点
   - posts：立柱 = 框内左右两侧「竖直连续 run 最长」的列（run 约 0.5~0.8 高，网只有 0.3 左右）
   - 顶宽 = 左上↔右上角的欧氏像素距离

对外主要入口：process_goal(frame, goal_xyxy, method="fused") -> 全图坐标的四角 + 顶宽。
遮挡过多导致立柱/网无法可靠区分时返回 None（放弃，而不是硬凑错误结果）。
"""

import math

import cv2
import numpy as np

# 白色阈值（HSV）：低饱和度 + 高亮度（人工调参结果，见 tune_hsv.py）
WHITE_LOWER = np.array([0, 0, 80], dtype=np.uint8)
WHITE_UPPER = np.array([180, 255, 255], dtype=np.uint8)

# Canny 双阈值（手动可调，见 main.py 的 "canny tune" trackbar）
CANNY_LOWER = 146
CANNY_UPPER = 255

# 立柱竖直白 run 高度阈值（占 ROI 高的比例）：立柱 ~0.5~0.8，网 ~0.3
POST_MIN_RUN_RATIO = 0.40

# 3×3 角点模板（hit-or-miss），编号习惯：
#   1 2 3
#   4 5 6
#   7 8 9
# 模板元素：1=白(前景)，-1=黑(背景)，0=不关心。
# TL（左上外角）：1,2,3,4,7 黑、其余白 —— 黑色 L 抱左上，白在右下。
# TR（右上外角）：1,2,3,6,9 黑、其余白 —— 镜像。
# 每组模板严格版在前、宽松版在后：严格版 9 像素全约束；宽松版只约束
# 「核心 L + 中心白」，右下三个像素（网区，时白时黑）不关心，
# 严格版匹配不到时兜底。
_TL_TEMPLATES = (
    np.array([[-1, -1, -1],
              [-1,  1,  1],
              [-1,  1,  1]], dtype=np.int8),
    np.array([[-1, -1, -1],
              [-1,  1,  0],
              [-1,  0,  0]], dtype=np.int8),
)
_TR_TEMPLATES = (
    np.array([[-1, -1, -1],
              [ 1,  1, -1],
              [ 1,  1, -1]], dtype=np.int8),
    np.array([[-1, -1, -1],
              [ 0,  1, -1],
              [ 0,  0, -1]], dtype=np.int8),
)


def expand_roi(xyxy, frame_shape, margin_side=0.2, margin_top=0.2, bottom_frac=0.5):
    """把 goal 框按比例外扩成 ROI，并 clamp 到图像边界（防越界）。

    margin_side: 水平方向左右各外扩框宽的比例。
    margin_top: 垂直方向上方外扩框高的比例。
    bottom_frac: 垂直方向向下保留框高的比例（0.5=只留框上半截）。
    只看横梁/立柱顶部时下方不需要太多，舍去下半截可减少地面/广告牌干扰。

    Returns:
        (x1, y1, x2, y2) 外扩后的 ROI，全图坐标，已在图像范围内。
    """
    x1, y1, x2, y2 = [int(round(v)) for v in xyxy]
    h, w = frame_shape[:2]
    dx = int((x2 - x1) * margin_side)
    dy = int((y2 - y1) * margin_top)
    bottom_frac = max(0.1, min(bottom_frac, 1.0))
    return (
        max(0, min(w, x1 - dx)),
        max(0, min(h, y1 - dy)),
        max(0, min(w, x2 + dx)),
        max(0, min(h, max(y1 + 1, y1 + int((y2 - y1) * bottom_frac)))),
    )


def white_mask(bgr, lower=None, upper=None):
    """HSV 白色阈值分割，返回 0/255 二值图（与输入同尺寸）。

    lower/upper 缺省时用模块级 WHITE_LOWER/WHITE_UPPER；
    传入时覆盖（供 main.py 的实时调参 trackbar 使用）。
    """
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    if lower is None:
        lower = WHITE_LOWER
    if upper is None:
        upper = WHITE_UPPER
    return cv2.inRange(hsv, lower, upper)


def otsu_mask(bgr):
    """大津法（Otsu）自适应阈值分割，返回 0/255 二值图。

    灰度图上自动找类间方差最大的阈值，把高亮门框与背景分开；
    每帧独立计算阈值，光照变化时自动适应。膨胀一次连接断裂的立柱。
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
    return mask


def canny_edges(bgr, lower=None, upper=None):
    """纯 Canny 边缘（高斯去噪，无膨胀/腐蚀），供 Hough 直线检测等使用。

    灰度 + 5x5 高斯模糊去噪。双阈值缺省用模块常量 CANNY_LOWER/UPPER
    （可被 main.py 的实时调参 trackbar 覆盖），不再自动计算。
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    if lower is None:
        lower = CANNY_LOWER
    if upper is None:
        upper = CANNY_UPPER
    return cv2.Canny(gray, lower, upper)


def edge_mask(bgr):
    """Canny 边缘检测生成 0/255 二值图（对光照变化比 HSV 颜色阈值更稳健）。

    = canny_edges + 3x3 闭运算（先膨胀后腐蚀）：
    - 膨胀把被遮挡/噪声打断的竖直线重新连接（立柱边缘断口）
    - 腐蚀收回膨胀的扩张，并消除小于结构元的孤立噪点
    """
    edges = canny_edges(bgr)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    return edges


def fused_mask(bgr, lower=None, upper=None):
    """HSV 白色区域 + Canny 边缘融合，返回 0/255 二值图。

    两种信息互补：
    - HSV 白色区域是「颜色先验」：门框材质的实心区域，语义直接，
      但光照过曝/偏色/变暗时会漏检；
    - Canny 边缘是「几何先验」：只依赖对比度，光照漂移时门框边界仍在，
      但背景杂物的边缘是噪声。

    融合 = 以 HSV 为锚，把「贴近白色区域的边缘」并入 mask：
        mask = hsv ∪ (edge ∩ dilate(hsv))
    远离白色区域的背景边缘被滤掉；HSV 漏检时，贴着的门框边界边缘
    仍能补上立柱轮廓，供 _find_posts 的竖直 run 检测使用。
    HSV 几乎完全失效（极端光照）时退化为纯边缘。
    """
    hsv = white_mask(bgr, lower, upper)
    edges = edge_mask(bgr)

    # 极端光照下 HSV 没选出任何东西，退化为纯边缘
    if (hsv > 0).mean() < 0.01:
        return edges

    # 容错带宽 = ROI 短边 4%（取奇数且 ≥3），白色区域周围一圈都算「贴近」
    k = int(round(min(hsv.shape[:2]) * 0.04))
    if k % 2 == 0:
        k += 1
    k = max(k, 3)
    anchor = cv2.dilate(hsv, np.ones((k, k), np.uint8))

    boundary_edges = cv2.bitwise_and(edges, anchor)
    return cv2.bitwise_or(hsv, boundary_edges)


def fused_otsu_mask(bgr, lower=None, upper=None):
    """HSV 白色区域 + 大津法融合，返回 0/255 二值图。

    与 fused_mask 同构，但把 Canny 边缘换成大津法前景：
        mask = hsv ∪ (otsu ∩ dilate(hsv))
    - HSV 为锚：白色语义，滤掉灯光/彩色高亮等干扰
    - 大津法每帧自适应亮度阈值：光照整体漂移（变暗/过曝导致 HSV
      漏检）时，贴近白色区域的大津法前景补上漏掉的门框
    - HSV 几乎完全失效（极端光照）时退化为纯大津法
    """
    hsv = white_mask(bgr, lower, upper)
    otsu = otsu_mask(bgr)

    # 极端光照下 HSV 没选出任何东西，退化为纯大津法
    if (hsv > 0).mean() < 0.01:
        return otsu

    # 容错带宽 = ROI 短边 4%（取奇数且 ≥3），白色区域周围一圈都算「贴近」
    k = int(round(min(hsv.shape[:2]) * 0.04))
    if k % 2 == 0:
        k += 1
    k = max(k, 3)
    anchor = cv2.dilate(hsv, np.ones((k, k), np.uint8))

    boundary = cv2.bitwise_and(otsu, anchor)
    return cv2.bitwise_or(hsv, boundary)


def build_mask(bgr, method="fused", lower=None, upper=None):
    """按指定方法生成门框二值图。

    fused=HSV+Canny边缘；fused_otsu=HSV+大津法；hsv=白色阈值；
    edge=Canny 边缘；otsu=大津法。
    lower/upper 在 method="hsv"/"fused"/"fused_otsu" 时生效（实时调参）。
    """
    if method == "fused":
        return fused_mask(bgr, lower, upper)
    if method == "fused_otsu":
        return fused_otsu_mask(bgr, lower, upper)
    if method == "otsu":
        return otsu_mask(bgr)
    if method == "edge":
        return edge_mask(bgr)
    return white_mask(bgr, lower, upper)


def _longest_run(bool_arr):
    """返回最长连续 True 段的 (start, end) 索引（含端点）；全 False 返回 None。"""
    best = None
    cur_start = None
    for i, v in enumerate(bool_arr):
        if v:
            if cur_start is None:
                cur_start = i
        elif cur_start is not None:
            run = (cur_start, i - 1)
            if best is None or (run[1] - run[0]) > (best[1] - best[0]):
                best = run
            cur_start = None
    if cur_start is not None:
        run = (cur_start, len(bool_arr) - 1)
        if best is None or (run[1] - run[0]) > (best[1] - best[0]):
            best = run
    return best


def _find_posts(mask, x_lo, x_hi):
    """在列范围 [x_lo, x_hi] 内找左右两根立柱的 x（列中心）。

    立柱是实心竖条：其列上有一段很长的连续白（~0.5~0.8 高）。
    网是斜网，竖直白 run 短（~0.3 高），用阈值分开。
    取最左/最右两个列簇作为立柱。返回 (left_x, right_x)，找不到返回 (None, None)。
    """
    h = mask.shape[0]
    min_run = int(h * POST_MIN_RUN_RATIO)
    post_cols = []
    for x in range(x_lo, x_hi + 1):
        run = _longest_run(mask[:, x] > 0)
        if run is not None and (run[1] - run[0] + 1) >= min_run:
            post_cols.append(x)

    if not post_cols:
        return None, None

    # 聚类相邻列（立柱有 2~4px 宽），取最左/最右两个簇的中心
    clusters = []
    start = prev = post_cols[0]
    for x in post_cols[1:]:
        if x - prev > 3:
            clusters.append((start, prev))
            start = x
        prev = x
    clusters.append((start, prev))

    left = clusters[0]
    right = clusters[-1]
    return int((left[0] + left[1]) / 2), int((right[0] + right[1]) / 2)


def _column_top_bottom(mask, x):
    """某列白像素的最上/最下 y，无白返回 None。"""
    col = mask[:, x] > 0
    ys = np.where(col)[0]
    if ys.size == 0:
        return None
    return int(ys[0]), int(ys[-1])


def _match_template(mask, templates, x_lo, x_hi):
    """按顺序尝试模板（严格→宽松），返回匹配点列表 [(x, y), ...]，全无返回 []。

    匹配点 = 3×3 窗口中心位置，即角点像素本身。
    """
    for kernel in templates:
        hits = cv2.morphologyEx(mask, cv2.MORPH_HITMISS, kernel)
        ys, xs = np.where(hits > 0)
        pts = [(int(x), int(y)) for x, y in zip(xs, ys)]
        pts = [p for p in pts if x_lo <= p[0] <= x_hi]
        if pts:
            return pts
    return []


def find_corners_by_template(mask, x_lo=None, x_hi=None):
    """3×3 模板匹配找球门左上/右上角点（ROI 内坐标）。

    TL 模板只在左半区 [x_lo, mid] 搜索，TR 只在右半区 [mid+1, x_hi]；
    每侧取最靠外的匹配点（TL 取 x 最小、TR 取 x 最大）。

    Returns:
        dict: {'TL','TR','top_width'}，任一侧找不到返回 None。
    """
    w = mask.shape[1]
    if x_lo is None:
        x_lo = 0
    if x_hi is None:
        x_hi = w - 1
    x_lo = max(0, min(x_lo, w - 1))
    x_hi = max(0, min(x_hi, w - 1))
    if x_hi <= x_lo:
        return None

    mid = (x_lo + x_hi) // 2
    tl_pts = _match_template(mask, _TL_TEMPLATES, x_lo, mid)
    tr_pts = _match_template(mask, _TR_TEMPLATES, mid + 1, x_hi)
    if not tl_pts or not tr_pts:
        return None

    tl = min(tl_pts, key=lambda p: p[0])
    tr = max(tr_pts, key=lambda p: p[0])
    return {
        "TL": tl,
        "TR": tr,
        "top_width": float(np.hypot(tr[0] - tl[0], tr[1] - tl[1])),
    }


def _line_intersection(p1, p2, p3, p4):
    """两线段所在直线的交点（交点可在线段延长线上）；平行返回 None。"""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return None
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom
    return int(round(px)), int(round(py))


def find_corners_hough(bgr_roi, box_xyxy_roi, lower=None, upper=None):
    """霍夫直线检测找球门角点（ROI 内坐标）。

    1. 在高斯去噪后的纯 Canny 边缘上跑 HoughLinesP
    2. 按角度分成近似水平线 / 左半区垂直线 / 右半区垂直线
    3. 横梁 = 框顶 ±30% 框高内的最长水平线；立柱 = 框左右边界 ±15% 框宽内
       每侧最长的垂直线
    4. 横梁直线与左右立柱直线的交点 = TL / TR

    Args:
        bgr_roi: ROI 区域 BGR 图。
        box_xyxy_roi: goal 框在 ROI 内的 (bx1, by1, bx2, by2)。
        lower/upper: Canny 双阈值（None 用模块常量，供实时调参）。

    Returns:
        dict: {'TL','TR','top_width'}（ROI 内坐标），找不到返回 None。
    """
    bx1, by1, bx2, by2 = [int(round(v)) for v in box_xyxy_roi]
    box_w = bx2 - bx1
    box_h = by2 - by1
    if box_w <= 0 or box_h <= 0:
        return None

    edges = canny_edges(bgr_roi, lower, upper)
    # 横梁长度 ≈ 框宽；立柱在 ROI 内可见长度 ≈ roi_bottom_frac×框高（ROI 矮时很短）。
    # 取两者较小值做 minLineLength，避免短 ROI 下立柱线被过滤掉。
    min_len = max(20, int(min(box_w * 0.25, box_h * 0.15)))
    max_gap = max(10, int(box_w * 0.10))
    threshold = max(30, int(min(edges.shape[:2]) * 0.06))
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=threshold,
                            minLineLength=min_len, maxLineGap=max_gap)
    if lines is None:
        return None
    # 兼容不同 OpenCV 版本的返回形状：(N,1,4) 或 (N,4)，统一成 (N,4)
    lines = lines.reshape(-1, 4)

    horiz, verts_left, verts_right = [], [], []
    mid_x = (bx1 + bx2) / 2
    for lx1, ly1, lx2, ly2 in lines:
        lx1, ly1, lx2, ly2 = int(lx1), int(ly1), int(lx2), int(ly2)
        dx, dy = lx2 - lx1, ly2 - ly1
        length = math.hypot(dx, dy)
        if length < min_len:
            continue
        if abs(dy) <= 0.35 * length:  # 近似水平（±20° 左右）
            horiz.append((lx1, ly1, lx2, ly2, length))
        elif abs(dx) <= 0.35 * length:  # 近似垂直
            cx = (lx1 + lx2) / 2
            if cx < mid_x:
                verts_left.append((lx1, ly1, lx2, ly2, length))
            else:
                verts_right.append((lx1, ly1, lx2, ly2, length))

    # 横梁：框顶附近（±30% 框高）的最长水平线
    beam_cands = [
        l for l in horiz
        if by1 - 0.3 * box_h <= (l[1] + l[3]) / 2 <= by1 + 0.3 * box_h
    ]
    if not beam_cands:
        return None
    beam = max(beam_cands, key=lambda l: l[4])

    # 立柱：框左右边界附近（±15% 框宽）每侧最长垂直线
    def _pick_post(verts, lo, hi):
        cands = [l for l in verts if lo <= (l[0] + l[2]) / 2 <= hi]
        if not cands:
            return None
        return max(cands, key=lambda l: l[4])

    post_l = _pick_post(verts_left, bx1 - 0.15 * box_w, mid_x)
    post_r = _pick_post(verts_right, mid_x, bx2 + 0.15 * box_w)
    if post_l is None or post_r is None:
        return None

    tl = _line_intersection((beam[0], beam[1]), (beam[2], beam[3]),
                            (post_l[0], post_l[1]), (post_l[2], post_l[3]))
    tr = _line_intersection((beam[0], beam[1]), (beam[2], beam[3]),
                            (post_r[0], post_r[1]), (post_r[2], post_r[3]))
    if tl is None or tr is None:
        return None

    return {
        "TL": tl,
        "TR": tr,
        "top_width": float(np.hypot(tr[0] - tl[0], tr[1] - tl[1])),
    }


def find_corners_shitomasi(mask, x_lo, x_hi, y_lo, y_hi):
    """Shi-Tomasi 角点检测（备选角点算法）。

    在 mask 的 [x_lo,x_hi]×[y_lo,y_hi] 区域内找角点——二值图的轮廓拐角
    就是强角点——取最左/最右两个作为 TL/TR。

    Returns:
        dict: {'TL','TR','top_width'}（ROI 内坐标），找不到返回 None。
    """
    h, w = mask.shape[:2]
    x_lo = max(0, min(x_lo, w - 1))
    x_hi = max(x_lo, min(x_hi, w - 1))
    y_lo = max(0, min(y_lo, h - 1))
    y_hi = max(y_lo, min(y_hi, h - 1))

    region = mask[y_lo:y_hi + 1, x_lo:x_hi + 1]
    if int(region.sum()) < 80:
        return None

    pts = cv2.goodFeaturesToTrack(region, maxCorners=40, qualityLevel=0.01,
                                  minDistance=10, blockSize=3)
    if pts is None or len(pts) < 2:
        return None
    pts = pts.reshape(-1, 2)
    pts[:, 0] += x_lo
    pts[:, 1] += y_lo

    tl = pts[pts[:, 0].argmin()]
    tr = pts[pts[:, 0].argmax()]
    tl = (int(tl[0]), int(tl[1]))
    tr = (int(tr[0]), int(tr[1]))
    if tr[0] - tl[0] < 5:
        return None

    return {
        "TL": tl,
        "TR": tr,
        "top_width": float(np.hypot(tr[0] - tl[0], tr[1] - tl[1])),
    }


def find_corners_poly(mask, x_lo=None, x_hi=None):
    """轮廓多边形逼近找球门直角点（ROI 内坐标）。

    门框白色区域的外轮廓逼近成多边形（approxPolyDP），顶边左右两个
    顶点就是横梁上沿两端 ≈ 左上/右上外角。不依赖 3×3 局部形态，
    对网线等细小结构更鲁棒。

    Returns:
        dict: {'TL','TR','top_width'}（ROI 内坐标），找不到返回 None。
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) < 100:
        return None

    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
    pts = [(int(p[0][0]), int(p[0][1])) for p in approx]

    if x_lo is not None and x_hi is not None:
        pts = [p for p in pts if x_lo <= p[0] <= x_hi]
    if len(pts) < 2:
        return None

    # 顶部顶点：取 y 最小的一批（横梁上沿），再取其中最左/最右两个
    top_y = min(p[1] for p in pts)
    y_cut = top_y + max(10, int(mask.shape[0] * 0.15))
    top_pts = [p for p in pts if p[1] <= y_cut]
    if len(top_pts) < 2:
        top_pts = pts

    tl = min(top_pts, key=lambda p: p[0])
    tr = max(top_pts, key=lambda p: p[0])
    if tr[0] - tl[0] < 5:
        return None

    return {
        "TL": tl,
        "TR": tr,
        "top_width": float(np.hypot(tr[0] - tl[0], tr[1] - tl[1])),
    }


def find_corners_row(mask, x_lo, x_hi, y_lo, y_hi):
    """最长横列（众数行）法找球门角点（ROI 内坐标）。

    横梁是门框里白色像素最多的一行：在框顶部区域内按行统计白像素数，
    取计数最大的一行作为横梁行，该行在搜索列范围内最左/最右的白像素
    即横梁两端 ≈ TL/TR。

    Returns:
        dict: {'TL','TR','top_width'}（ROI 内坐标），找不到返回 None。
    """
    h, w = mask.shape[:2]
    x_lo = max(0, min(x_lo, w - 1))
    x_hi = max(x_lo, min(x_hi, w - 1))
    y_lo = max(0, min(y_lo, h - 1))
    y_hi = max(y_lo, min(y_hi, h - 1))

    region = mask[y_lo:y_hi + 1, x_lo:x_hi + 1]
    counts = (region > 0).sum(axis=1)
    if int(counts.max()) < max(10, int((x_hi - x_lo) * 0.1)):
        return None
    beam_y = y_lo + int(counts.argmax())

    row_px = np.where(mask[beam_y, x_lo:x_hi + 1] > 0)[0]
    if row_px.size < 2:
        return None
    tl = (x_lo + int(row_px[0]), beam_y)
    tr = (x_lo + int(row_px[-1]), beam_y)
    if tr[0] - tl[0] < 5:
        return None

    return {
        "TL": tl,
        "TR": tr,
        "top_width": float(np.hypot(tr[0] - tl[0], tr[1] - tl[1])),
    }


def find_goal_corners(mask, x_lo=None, x_hi=None):
    """在 ROI 的白色 mask 中找球门角点（ROI 内坐标）。

    主要目标：左上角 TL、右上角 TR，以及它们的像素距离 top_width。
    底部角点 BL/BR 只作为兜底返回：当左上/右上某一边拿不到（立柱顶端被遮挡）时，
    可以用底部角点来估算距离。

    Args:
        mask: ROI 的白色二值图（0/255）。
        x_lo, x_hi: 立柱搜索的列范围（默认整幅宽），用于把搜索限制在 goal 框内。

    Returns:
        dict: {'TL', 'TR', 'top_width', 'BL', 'BR'}，ROI 内像素坐标；
              top_width 为左上↔右上角的欧氏像素距离。找不到返回 None。
    """
    if int(mask.sum()) < 80:
        return None

    w = mask.shape[1]
    if x_lo is None:
        x_lo = 0
    if x_hi is None:
        x_hi = w - 1
    x_lo = max(0, min(x_lo, w - 1))
    x_hi = max(0, min(x_hi, w - 1))
    if x_hi <= x_lo:
        return None

    # 1) 立柱
    left_x, right_x = _find_posts(mask, x_lo, x_hi)
    if left_x is None or right_x is None or left_x == right_x:
        return None

    # 2) 立柱顶/底
    left_tb = _column_top_bottom(mask, left_x)
    right_tb = _column_top_bottom(mask, right_x)
    if left_tb is None or right_tb is None:
        return None

    # 角点用各自立柱的顶端（考虑透视，左右立柱顶端可能不在同一高度）
    tl = (left_x, left_tb[0])
    tr = (right_x, right_tb[0])
    top_width = float(np.hypot(tr[0] - tl[0], tr[1] - tl[1]))

    return {
        "TL": tl,
        "TR": tr,
        "BL": (left_x, left_tb[1]),
        "BR": (right_x, right_tb[1]),
        "top_width": top_width,
    }


def process_goal(frame, goal_xyxy, margin_side=0.2, margin_top=0.2, method="fused",
                 lower=None, upper=None, corner_method="auto", roi_bottom_frac=0.5,
                 canny_lower=None, canny_upper=None):
    """对一帧里的一个 goal 框，返回全图坐标的四角与顶宽。

    Args:
        margin_side: ROI 水平方向左右各外扩框宽的比例。
        margin_top: ROI 垂直方向上方外扩框高的比例。
        method: 分割方法，"fused"=HSV+边缘融合（默认），"hsv"=白色阈值，
                "edge"=Canny 边缘，"otsu"=大津法。
        lower/upper: 在 method="hsv"/"fused" 时生效的 HSV 阈值（实时调参）。
        corner_method: 角点定位方法。"auto"=依次回退
                hough(霍夫直线) → row(最长横列/众数行) → template(3×3模板)
                → poly(轮廓多边形逼近) → shitomasi → posts(立柱run)；
                也可显式指定其中一种（失败仍回退 posts）。
        roi_bottom_frac: ROI 垂直方向向下保留框高的比例（默认 0.5）。
                只需横梁与立柱顶部，舍去下半截减少干扰。
        canny_lower/canny_upper: hough 用的 Canny 双阈值（None 用模块常量，
                实时调参）。

    Returns:
        dict: {'TL','TR','BL','BR','top_width','source'} 全图坐标，或 None。
              source 记录角点实际来源（调试用）。
    """
    x1, y1, x2, y2 = expand_roi(goal_xyxy, frame.shape,
                                margin_side, margin_top, roi_bottom_frac)
    if x2 <= x1 or y2 <= y1:
        return None
    roi = frame[y1:y2, x1:x2]
    mask = build_mask(roi, method, lower, upper)

    # goal 框在 ROI 内的坐标（立柱就在框附近，略微外扩以容错框裁掉立柱的情况）
    box_x1 = int(round(goal_xyxy[0])) - x1
    box_x2 = int(round(goal_xyxy[2])) - x1
    box_y1_roi = int(round(goal_xyxy[1])) - y1
    box_y2_roi = int(round(goal_xyxy[3])) - y1
    pad = int((box_x2 - box_x1) * 0.08)
    search_lo, search_hi = box_x1 - pad, box_x2 + pad

    # 角点定位链：按 corner_method 依次尝试，最终回退立柱 run（posts）
    corners = None
    if corner_method in ("auto", "hough"):
        # 纯 Canny + 霍夫：不经过 mask/二值化，直接对 mask 用的小 ROI 原图做。
        # 在框顶附近筛水平长线（横梁）、框左右附近筛垂直线（立柱），求交点。
        c = find_corners_hough(
            roi, (box_x1, box_y1_roi, box_x2, box_y2_roi),
            canny_lower, canny_upper,
        )
        if c is not None:
            c["source"] = "hough"
            c["BL"] = c["BR"] = None
        corners = c
    if corners is None and corner_method in ("auto", "row"):
        # 最长横列法：mask 上白像素最多的行 = 横梁，两端 = TL/TR
        box_h_roi = box_y2_roi - box_y1_roi
        c = find_corners_row(
            mask, search_lo, search_hi,
            box_y1_roi - int(0.1 * box_h_roi),
            box_y1_roi + int(0.5 * box_h_roi),
        )
        if c is not None:
            c["source"] = "row"
            c["BL"] = c["BR"] = None
        corners = c
    if corners is None and corner_method in ("auto", "template"):
        c = find_corners_by_template(mask, search_lo, search_hi)
        if c is not None:
            c["source"] = "template"
            c["BL"] = c["BR"] = None
        corners = c
    if corners is None and corner_method in ("auto", "poly"):
        c = find_corners_poly(mask, search_lo, search_hi)
        if c is not None:
            c["source"] = "poly"
            c["BL"] = c["BR"] = None
        corners = c
    if corners is None and corner_method in ("auto", "shitomasi"):
        c = find_corners_shitomasi(
            mask, search_lo, search_hi,
            box_y1_roi, box_y1_roi + int(0.6 * (box_y2_roi - box_y1_roi)),
        )
        if c is not None:
            c["source"] = "shitomasi"
            c["BL"] = c["BR"] = None
        corners = c
    if corners is None:
        corners = find_goal_corners(mask, search_lo, search_hi)
        if corners is None:
            return None
        corners["source"] = "posts"
        if roi_bottom_frac < 1.0:
            # ROI 只含框上半截，立柱底端不在 ROI 内，BL/BR 无意义
            corners["BL"] = corners["BR"] = None

    # 合理性校验 1：顶宽应大致等于框宽（立柱在框左右边界附近）
    box_w = float(goal_xyxy[2] - goal_xyxy[0])
    if not (0.5 * box_w <= corners["top_width"] <= 1.3 * box_w):
        return None

    # 合理性校验 2：角点高度应在门框顶部附近（横梁就在框顶；用 ROI 内坐标比较）
    box_h = float(goal_xyxy[3] - goal_xyxy[1])
    for k in ("TL", "TR"):
        if not (box_y1_roi - 0.1 * box_h <= corners[k][1] <= box_y1_roi + 0.6 * box_h):
            return None

    corners.setdefault("BL", None)
    corners.setdefault("BR", None)
    for k in ("TL", "TR", "BL", "BR"):
        p = corners[k]
        if p is None:
            continue
        cx, cy = p
        corners[k] = (cx + x1, cy + y1)
    return corners

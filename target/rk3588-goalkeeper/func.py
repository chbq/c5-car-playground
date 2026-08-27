#以下代码改自https://github.com/rockchip-linux/rknn-toolkit2/tree/master/examples/onnx/yolov5
import cv2
import numpy as np

OBJ_THRESH, NMS_THRESH, IMG_SIZE = 0.25, 0.2, 640

CLASSES = ("football", "goal")

FOOTBALL_CLASS_ID = 0   # 足球
GOAL_CLASS_ID = 1       # 球门


def filter_boxes(boxes, box_confidences, box_class_probs):
    """Filter boxes with object threshold.
    """
    box_confidences = box_confidences.reshape(-1)
    candidate, class_num = box_class_probs.shape

    class_max_score = np.max(box_class_probs, axis=-1)
    classes = np.argmax(box_class_probs, axis=-1)

    _class_pos = np.where(class_max_score* box_confidences >= OBJ_THRESH)
    scores = (class_max_score* box_confidences)[_class_pos]

    boxes = boxes[_class_pos]
    classes = classes[_class_pos]

    return boxes, classes, scores

def nms_boxes(boxes, scores):
    """Suppress non-maximal boxes.
    # Returns
        keep: ndarray, index of effective boxes.
    """
    x = boxes[:, 0]
    y = boxes[:, 1]
    w = boxes[:, 2] - boxes[:, 0]
    h = boxes[:, 3] - boxes[:, 1]

    areas = w * h
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)

        xx1 = np.maximum(x[i], x[order[1:]])
        yy1 = np.maximum(y[i], y[order[1:]])
        xx2 = np.minimum(x[i] + w[i], x[order[1:]] + w[order[1:]])
        yy2 = np.minimum(y[i] + h[i], y[order[1:]] + h[order[1:]])

        w1 = np.maximum(0.0, xx2 - xx1 + 0.00001)
        h1 = np.maximum(0.0, yy2 - yy1 + 0.00001)
        inter = w1 * h1

        ovr = inter / (areas[i] + areas[order[1:]] - inter)
        inds = np.where(ovr <= NMS_THRESH)[0]
        order = order[inds + 1]
    keep = np.array(keep)
    return keep

# def dfl(position):
#     # Distribution Focal Loss (DFL)
#     import torch
#     x = torch.tensor(position)
#     n,c,h,w = x.shape
#     p_num = 4
#     mc = c//p_num
#     y = x.reshape(n,p_num,mc,h,w)
#     y = y.softmax(2)
#     acc_metrix = torch.tensor(range(mc)).float().reshape(1,1,mc,1,1)
#     y = (y*acc_metrix).sum(2)
#     return y.numpy()

# def dfl(position):
#     # Distribution Focal Loss (DFL)
#     n, c, h, w = position.shape
#     p_num = 4
#     mc = c // p_num
#     y = position.reshape(n, p_num, mc, h, w)
#     exp_y = np.exp(y)
#     y = exp_y / np.sum(exp_y, axis=2, keepdims=True)
#     acc_metrix = np.arange(mc).reshape(1, 1, mc, 1, 1).astype(float)
#     y = (y * acc_metrix).sum(2)
#     return y

def dfl(position):
    # Distribution Focal Loss (DFL)
    # x = np.array(position)
    n,c,h,w = position.shape
    p_num = 4
    mc = c//p_num
    y = position.reshape(n,p_num,mc,h,w)

    # Vectorized softmax
    e_y = np.exp(y - np.max(y, axis=2, keepdims=True))  # subtract max for numerical stability
    y = e_y / np.sum(e_y, axis=2, keepdims=True)

    acc_metrix = np.arange(mc).reshape(1,1,mc,1,1)
    y = (y*acc_metrix).sum(2)
    return y


def box_process(position):
    grid_h, grid_w = position.shape[2:4]
    col, row = np.meshgrid(np.arange(0, grid_w), np.arange(0, grid_h))
    col = col.reshape(1, 1, grid_h, grid_w)
    row = row.reshape(1, 1, grid_h, grid_w)
    grid = np.concatenate((col, row), axis=1)
    stride = np.array([IMG_SIZE//grid_h, IMG_SIZE//grid_w]).reshape(1,2,1,1)

    position = dfl(position)
    box_xy  = grid +0.5 -position[:,0:2,:,:]
    box_xy2 = grid +0.5 +position[:,2:4,:,:]
    xyxy = np.concatenate((box_xy*stride, box_xy2*stride), axis=1)

    return xyxy

_PRINTED_OUTPUT_SHAPES = False


def yolov8_post_process(input_data):
    """ultralytics RKNN 导出格式后处理。

    football_8_16_100.rknn 输出单张量 (1, 4+nc, 8400)：已 DFL 解码并 concat，
    前 4 通道 = xywh 框 [cx, cy, w, h]（640 推理空间），后 nc 通道 = class score（已 sigmoid）。
    8400 = 80*80 + 40*40 + 20*20。
    """
    global _PRINTED_OUTPUT_SHAPES

    preds = input_data[0]
    if preds.ndim == 3:
        preds = preds[0]  # (1, 6, 8400) -> (6, 8400)
    preds = preds.T       # (6, 8400) -> (8400, 6)

    boxes = preds[:, :4]      # xywh: [cx, cy, w, h]，640 空间
    cls_scores = preds[:, 4:]  # (8400, nc)

    classes = np.argmax(cls_scores, axis=1)
    scores = cls_scores.max(axis=1)

    keep = np.where(scores >= OBJ_THRESH)[0]
    boxes = boxes[keep]
    classes = classes[keep]
    scores = scores[keep]

    if not _PRINTED_OUTPUT_SHAPES:
        _PRINTED_OUTPUT_SHAPES = True
        print(
            f"[RKNN] 输出张量数={len(input_data)} "
            f"shapes={[getattr(t, 'shape', None) for t in input_data]} "
            f"dtypes={[getattr(t, 'dtype', None) for t in input_data]}"
        )
        print(
            f"[RKNN] 检出={boxes.shape[0]} 前3框(反算前)={boxes[:3].tolist()} "
            f"classes={classes[:3].tolist()} scores={scores[:3].tolist()}"
        )

    if boxes.shape[0] == 0:
        return None, None, None

    # 模型输出 xywh [cx, cy, w, h] → 转 xyxy [x1, y1, x2, y2]
    # （下游 nms_boxes / draw / tracker 均按 xyxy 处理）
    cx = boxes[:, 0]
    cy = boxes[:, 1]
    w = boxes[:, 2]
    h = boxes[:, 3]
    boxes = np.stack(
        [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1
    )

    # 每类分别 NMS（沿用 nms_boxes，输入 xyxy）
    nboxes, nclasses, nscores = [], [], []
    for c in set(classes):
        inds = np.where(classes == c)[0]
        b = boxes[inds]
        s = scores[inds]
        keep_idx = nms_boxes(b, s)
        if len(keep_idx):
            nboxes.append(b[keep_idx])
            nclasses.append(classes[inds][keep_idx])
            nscores.append(s[keep_idx])

    if not nboxes:
        return None, None, None

    boxes = np.concatenate(nboxes)
    classes = np.concatenate(nclasses)
    scores = np.concatenate(nscores)
    return boxes, classes, scores

def draw(image, boxes, scores, classes):
    """在原始图像上画检测框。boxes 应为原始图像坐标。"""
    CLASS_COLORS = {
        FOOTBALL_CLASS_ID: ((255, 100, 0), (200, 100, 50)),  # BGR: 蓝框橙字
        GOAL_CLASS_ID:     ((0, 200, 0), (0, 180, 0)),        # 绿框深绿字
    }
    DEFAULT_COLOR = ((255, 0, 0), (0, 0, 255))  # 默认蓝框红字

    for box, score, cl in zip(boxes, scores, classes):
        left, top, right, bottom = box
        left, top, right, bottom = int(left), int(top), int(right), int(bottom)

        box_color, text_color = CLASS_COLORS.get(cl, DEFAULT_COLOR)
        cv2.rectangle(image, (left, top), (right, bottom), box_color, 2)
        cv2.putText(image, '{0} {1:.2f}'.format(CLASSES[cl], score),
                    (left, top - 6),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, text_color, 2)

def letterbox(im, new_shape=(640, 640), color=(0, 0, 0)):
    shape = im.shape[:2]  # current shape [height, width]
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])

    ratio = r, r  # width, height ratios
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - \
        new_unpad[1]  # wh padding

    dw /= 2  # divide padding into 2 sides
    dh /= 2

    if shape[::-1] != new_unpad:  # resize
        im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    im = cv2.copyMakeBorder(im, top, bottom, left, right,
                            cv2.BORDER_CONSTANT, value=color)  # add border
    #return im
    return im, ratio, (left, top)

def _get_best_detection_box(boxes, classes, scores, class_id):
    """提取指定类别置信度最高的目标及其检测框尺寸。"""
    if boxes is None or len(classes) == 0:
        return None

    best_score = 0
    best = None
    for box, cls, score in zip(boxes, classes, scores):
        if cls == class_id and score > best_score:
            # box: [left, top, right, bottom]
            x_center = int((box[0] + box[2]) / 2)
            y_center = int((box[1] + box[3]) / 2)
            width = max(0, int(round(box[2] - box[0])))
            height = max(0, int(round(box[3] - box[1])))
            best = (x_center, y_center, width, height, float(score))
            best_score = score
    return best


def _get_best_detection(boxes, classes, scores, class_id):
    """提取指定类别置信度最高目标的中心和置信度。"""
    detection = _get_best_detection_box(boxes, classes, scores, class_id)
    if detection is None:
        return None
    x_center, y_center, _, _, score = detection
    return x_center, y_center, score


def get_football(boxes, classes, scores):
    """从检测结果中提取置信度最高的足球。"""
    return _get_best_detection(boxes, classes, scores, FOOTBALL_CLASS_ID)


def get_football_box(boxes, classes, scores):
    """返回足球中心、检测框宽高和置信度。"""
    return _get_best_detection_box(
        boxes, classes, scores, FOOTBALL_CLASS_ID)


def get_goal(boxes, classes, scores):
    """从检测结果中提取置信度最高的球门。"""
    return _get_best_detection(boxes, classes, scores, GOAL_CLASS_ID)


def _get_best_detection_xyxy(boxes, classes, scores, class_id):
    """提取指定类别置信度最高的目标的原始框 [x1,y1,x2,y2] 与置信度。"""
    if boxes is None or len(classes) == 0:
        return None

    best_score = 0
    best = None
    for box, cls, score in zip(boxes, classes, scores):
        if cls == class_id and score > best_score:
            # box: [left, top, right, bottom]（原始图像坐标）
            best = (float(box[0]), float(box[1]),
                    float(box[2]), float(box[3]), float(score))
            best_score = score
    return best


def get_goal_box(boxes, classes, scores):
    """返回置信度最高的球门检测框 [x1,y1,x2,y2] 和置信度；无球门返回 None。"""
    return _get_best_detection_xyxy(boxes, classes, scores, GOAL_CLASS_ID)


def myFunc(rknn_lite, IMG):
    IMG2 = cv2.cvtColor(IMG, cv2.COLOR_BGR2RGB)
    # 等比例缩放
    IMG2, ratio, padding = letterbox(IMG2)
    # 强制放缩
    # IMG2 = cv2.resize(IMG, (IMG_SIZE, IMG_SIZE))
    IMG2 = np.expand_dims(IMG2, 0)

    outputs = rknn_lite.inference(inputs=[IMG2], data_format=['nhwc'])

    boxes, classes, scores = yolov8_post_process(outputs)

    annotated = IMG
    if boxes is not None:
        # 将 boxes 从 640 推理空间转换回原始图像坐标
        # box: [x1, y1, x2, y2], padding: (left, top), ratio: (w_ratio, h_ratio)
        boxes[:, 0] = (boxes[:, 0] - padding[0]) / ratio[0]  # x1
        boxes[:, 1] = (boxes[:, 1] - padding[1]) / ratio[1]  # y1
        boxes[:, 2] = (boxes[:, 2] - padding[0]) / ratio[0]  # x2
        boxes[:, 3] = (boxes[:, 3] - padding[1]) / ratio[1]  # y2

        # 在副本上画框，保留干净 IMG 给球门几何（边缘/角点检测不能被画的框污染）
        annotated = IMG.copy()
        draw(annotated, boxes, scores, classes)

    return IMG, annotated, boxes, classes, scores

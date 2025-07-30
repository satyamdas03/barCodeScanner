# import cv2
# import datetime
# import json
# import os
# import requests
# from dbr import BarcodeReader, BarcodeReaderError, EnumImagePixelFormat

# LICENSE_KEY = (
#     "t0083YQEAAGQ/nZ9V45+jqSPaJwGghLZDd04v/hoqbwwVPGgLnC3QwL1qgx"
#     "Tx9tUiGNeu7m0bwK3lPZZxcm2RoTap3kKrZ07G903jfXP2zOosO25iSS0=;"
#     "t0083YQEAAKf2Zhl7lLiiRehRsodUsYBL2c1CRwX5hIIIE69zTnZz6NbqSmd"
#     "+0eR2f5HuRtuQk3eI4x8KqFJ857w9joR2xhSZvm8a75vZI6oz7+Z9ScM=;"
#     "t0083YQEAAEDDW+I2S64gG4lZ0Sfnf6YKoteqqpb1tkD1zOBGFzU7df9l8Yd"
#     "PkMmTNufNp7mSvYB2kScN2MjV1cp7xyhUSaYzfd803jezRzSn7PNnSc4="
# )

# # 1) License initialization
# error_code, error_msg = BarcodeReader.init_license(LICENSE_KEY)
# if error_code != 0:
#     print(f"License init failed ({error_code}): {error_msg}")
#     exit(1)
# reader = BarcodeReader()

# def draw_bbox(frame, pts):
#     """
#     Draw a green polygon around the detected barcode/QR code.
#     Handles pts as either objects with .x/.y or plain tuples.
#     """
#     # normalize points to (x, y) tuples
#     norm_pts = []
#     for p in pts:
#         if hasattr(p, 'x') and hasattr(p, 'y'):
#             norm_pts.append((p.x, p.y))
#         else:
#             norm_pts.append((int(p[0]), int(p[1])))
#     # draw lines
#     for i in range(len(norm_pts)):
#         p1 = norm_pts[i]
#         p2 = norm_pts[(i + 1) % len(norm_pts)]
#         cv2.line(frame, p1, p2, (0, 255, 0), 2)

# def lookup_barcode(code: str) -> dict:
#     """
#     Query public APIs for product metadata.
#     """
#     headers = {
#         "User-Agent": "Mozilla/5.0 ...",
#         "Accept": "application/json"
#     }
#     # Normalize UPC‑A / EAN‑13
#     if len(code) == 11 and code.isdigit():
#         code = "0" + code
#     elif len(code) == 13 and code.startswith("0"):
#         code = code[1:]
#     # 1) BarcodeMonster
#     try:
#         r = requests.get(f"https://barcode.monster/api/{code}?json=1",
#                          headers=headers, timeout=3)
#         if r.ok and r.json().get("product"):
#             d = r.json()
#             return {
#                 "title":       d.get("product"),
#                 "brand":       d.get("brand"),
#                 "description": d.get("description") or d.get("product"),
#                 "category":    d.get("category")
#             }
#     except Exception:
#         pass
#     # 2) UPCitemdb
#     try:
#         r = requests.get("https://api.upcitemdb.com/prod/trial/lookup",
#                          params={"upc": code}, headers=headers, timeout=3)
#         items = r.json().get("items", [])
#         if items:
#             item = items[0]
#             return {
#                 "title":       item.get("title") or item.get("model"),
#                 "brand":       item.get("brand"),
#                 "description": item.get("description") or item.get("title"),
#                 "category":    item.get("category")
#             }
#     except Exception:
#         pass
#     # 3) OpenFoodFacts
#     try:
#         r = requests.get(
#             f"https://world.openfoodfacts.org/api/v0/product/{code}.json",
#             headers=headers, timeout=3
#         )
#         data = r.json()
#         if data.get("status") == 1:
#             prod = data["product"]
#             return {
#                 "title":       prod.get("product_name"),
#                 "brand":       prod.get("brands"),
#                 "description": prod.get("generic_name") or prod.get("product_name"),
#                 "category":    prod.get("categories") or ", ".join(prod.get("categories_tags", []))
#             }
#     except Exception:
#         pass
#     # 4) Google Shopping via SerpAPI
#     try:
#         r = requests.get("https://serpapi.com/search",
#                          params={
#                              "engine":  "google_shopping",
#                              "q":       code,
#                              "api_key": "cb63db8d175d05d36b0350e43cc05cdcd2d97578bac620dbb523582bab236f00"
#                          },
#                          headers=headers, timeout=3)
#         results = r.json().get("shopping_results", [])
#         if results:
#             res = results[0]
#             return {
#                 "title":       res.get("title"),
#                 "brand":       res.get("source"),
#                 "description": res.get("description"),
#                 "category":    res.get("category")
#             }
#     except Exception:
#         pass
#     return {"title": None, "brand": None, "description": None, "category": None}

# def main():
#     log_path = "barcodes.json"
#     records = json.load(open(log_path, "r")) if os.path.exists(log_path) else []
#     seen = {r["code"] for r in records}

#     cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
#     if not cap.isOpened():
#         cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
#     if not cap.isOpened():
#         print("Cannot open camera")
#         return

#     try:
#         while True:
#             ret, frame = cap.read()
#             if not ret:
#                 break

#             # Decode via dbr.decode_buffer
#             try:
#                 results = reader.decode_buffer(frame, EnumImagePixelFormat.IPF_BGR_888)
#             except BarcodeReaderError:
#                 results = None

#             # Treat None as empty list
#             if results is None:
#                 results = []

#             for res in results:
#                 code, btype = res.barcode_text, res.barcode_format_string
#                 if not code or code in seen:
#                     continue

#                 pts = res.localization_result.localization_points
#                 draw_bbox(frame, pts)
#                 # get a text position from normalized pts
#                 if hasattr(pts[0], 'x'):
#                     text_pos = (pts[0].x, pts[0].y - 10)
#                 else:
#                     text_pos = (int(pts[0][0]), int(pts[0][1] - 10))

#                 cv2.putText(frame,
#                             f"{code} ({btype})",
#                             text_pos,
#                             cv2.FONT_HERSHEY_SIMPLEX,
#                             0.6, (0, 255, 0), 2)

#                 info = lookup_barcode(code)
#                 rec = {
#                     "timestamp": datetime.datetime.now().isoformat(),
#                     "type":      btype,
#                     "code":      code,
#                     **info
#                 }
#                 records.append(rec)
#                 seen.add(code)
#                 with open(log_path, "w", encoding="utf-8") as f:
#                     json.dump(records, f, indent=2, ensure_ascii=False)

#             cv2.imshow("DBR Scanner — press 'q' to quit", frame)
#             if cv2.waitKey(1) & 0xFF == ord("q"):
#                 break

#     finally:
#         cap.release()
#         cv2.destroyAllWindows()

# if __name__ == "__main__":
#     main()


























import cv2
import datetime
import json
import os
import re
import requests
import easyocr
import matplotlib.pyplot as plt
from dbr import BarcodeReader, BarcodeReaderError, EnumImagePixelFormat

# ───── License & DBR Init ─────
LICENSE_KEY = (
    "t0083YQEAAGQ/nZ9V45+jqSPaJwGghLZDd04v/hoqbwwVPGgLnC3QwL1qgx"
    "Tx9tUiGNeu7m0bwK3lPZZxcm2RoTap3kKrZ07G903jfXP2zOosO25iSS0=;"
    "t0083YQEAAKf2Zhl7lLiiRehRsodUsYBL2c1CRwX5hIIIE69zTnZz6NbqSmd"
    "+0eR2f5HuRtuQk3eI4x8KqFJ857w9joR2xhSZvm8a75vZI6oz7+Z9ScM=;"
    "t0083YQEAAEDDW+I2S64gG4lZ0Sfnf6YKoteqqpb1tkD1zOBGFzU7df9l8Yd"
    "PkMmTNufNp7mSvYB2kScN2MjV1cp7xyhUSaYzfd803jezRzSn7PNnSc4="
)
err, msg = BarcodeReader.init_license(LICENSE_KEY)
if err != 0:
    raise RuntimeError(f"License init failed ({err}): {msg}")
reader = BarcodeReader()

# ───── EasyOCR Init ─────
ocr_reader = easyocr.Reader(['en'], gpu=False)

# ───── Helper Functions ─────
def draw_bbox(frame, pts):
    norm = [(p.x, p.y) if hasattr(p, 'x') else (int(p[0]), int(p[1])) for p in pts]
    for i in range(len(norm)):
        cv2.line(frame, norm[i], norm[(i+1)%len(norm)], (0,255,0), 2)

def lookup_barcode(code: str) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }
    if len(code)==11 and code.isdigit():
        code = "0"+code
    elif len(code)==13 and code.startswith("0"):
        code = code[1:]

    # BarcodeMonster
    try:
        r = requests.get(f"https://barcode.monster/api/{code}?json=1",
                         headers=headers, timeout=3)
        if r.ok and r.json().get("product"):
            d = r.json()
            return {
                "title": d.get("product"),
                "brand": d.get("brand"),
                "description": d.get("description") or d.get("product"),
                "category": d.get("category")
            }
    except:
        pass

    # UPCitemdb
    try:
        r = requests.get("https://api.upcitemdb.com/prod/trial/lookup",
                         params={"upc": code}, headers=headers, timeout=3)
        items = r.json().get("items", [])
        if items:
            item = items[0]
            return {
                "title": item.get("title") or item.get("model"),
                "brand": item.get("brand"),
                "description": item.get("description") or item.get("title"),
                "category": item.get("category")
            }
    except:
        pass

    # OpenFoodFacts
    try:
        r = requests.get(f"https://world.openfoodfacts.org/api/v0/product/{code}.json",
                         headers=headers, timeout=3)
        data = r.json()
        if data.get("status")==1:
            prod = data["product"]
            return {
                "title": prod.get("product_name"),
                "brand": prod.get("brands"),
                "description": prod.get("generic_name") or prod.get("product_name"),
                "category": prod.get("categories") or ", ".join(prod.get("categories_tags", []))
            }
    except:
        pass

    # SerpAPI Google Shopping
    try:
        r = requests.get("https://serpapi.com/search",
                         params={
                             "engine":  "google_shopping",
                             "q":       code,
                             "api_key": "cb63db8d175d05d36b0350e43cc05cdcd2d97578bac620dbb523582bab236f00"
                         }, headers=headers, timeout=3)
        res_list = r.json().get("shopping_results", [])
        if res_list:
            res = res_list[0]
            return {
                "title":       res.get("title"),
                "brand":       res.get("source"),
                "description": res.get("description"),
                "category":    res.get("category")
            }
    except:
        pass

    return {"title": None, "brand": None, "description": None, "category": None}

def extract_number_easyocr(roi):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.bilateralFilter(gray, 9,75,75)
    _, thresh = cv2.threshold(blur, 150,255, cv2.THRESH_BINARY_INV)
    texts = ocr_reader.readtext(thresh, detail=0)
    for t in texts:
        m = re.search(r"\d+\.?\d*", t)
        if m:
            return m.group(0)
    return None

def show_frame(frame):
    try:
        cv2.imshow("Scanner + EasyOCR", frame)
    except cv2.error:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        plt.ion()
        plt.imshow(rgb); plt.axis('off'); plt.pause(0.001)

def main():
    log_path = "barcodes.json"
    records = json.load(open(log_path,"r")) if os.path.exists(log_path) else []
    seen = {r["code"] for r in records}

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # --- Correct decode_buffer call ---
            h, w, c = frame.shape
            try:
                codes = reader.decode_buffer(
                    frame.tobytes(),
                    w,
                    h,
                    EnumImagePixelFormat.IPF_BGR_888
                ) or []
            except BarcodeReaderError:
                codes = []

            print("Found barcodes:", [r.barcode_text for r in codes])

            # OCR ROIs
            H, W = frame.shape[:2]
            mrp_roi = frame[int(0.2*H):int(0.4*H), int(0.6*W):int(0.95*W)]
            qty_roi = frame[int(0.4*H):int(0.6*H), int(0.6*W):int(0.95*W)]

            mrp_val = extract_number_easyocr(mrp_roi)
            qty_val = extract_number_easyocr(qty_roi)

            for res in codes:
                code = res.barcode_text
                if not code or code in seen:
                    continue

                pts = res.localization_result.localization_points
                draw_bbox(frame, pts)
                x, y = (pts[0].x, pts[0].y) if hasattr(pts[0],'x') else (int(pts[0][0]),int(pts[0][1]))
                cv2.putText(frame, code, (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

                info = lookup_barcode(code)
                rec = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "code":      code,
                    "mrp":       mrp_val,
                    "quantity":  qty_val,
                    **info
                }
                records.append(rec)
                seen.add(code)
                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump(records, f, indent=2, ensure_ascii=False)

            show_frame(frame)

            try:
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except cv2.error:
                pass

    finally:
        cap.release()
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            plt.close('all')

if __name__ == "__main__":
    main()


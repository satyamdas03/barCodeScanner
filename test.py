import cv2
import datetime
import json
import os
import requests

def validate_ean_generic(code: str) -> bool:
    """
    Validate an EAN‑8 or EAN‑13 code using its check‑digit.
    """
    if len(code) not in (8, 13) or not code.isdigit():
        return False
    digits = list(map(int, code))
    checksum = digits.pop()      # last digit
    digits.reverse()             # prepare for weighting from right
    total = sum(d * (3 if i % 2 == 0 else 1)
                for i, d in enumerate(digits))
    return (10 - (total % 10)) % 10 == checksum

def validate_upca(code: str) -> bool:
    """
    Validate a UPC‑A code by treating it as an EAN‑13 with a leading zero.
    """
    if len(code) != 12 or not code.isdigit():
        return False
    return validate_ean_generic("0" + code)

def draw_bbox(frame, pts):
    """
    Draw a green polygon around the detected barcode/QR code.
    """
    pts = pts.astype(int).reshape(-1, 2)
    for i in range(len(pts)):
        pt1 = tuple(pts[i])
        pt2 = tuple(pts[(i + 1) % len(pts)])
        cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

def lookup_barcode(code: str) -> dict:
    """
    Query multiple public APIs for product metadata.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ),
        "Accept": "application/json"
    }
    # Normalize UPC‑A / EAN‑13 codes
    if len(code) == 11 and code.isdigit():
        code = "0" + code
    elif len(code) == 13 and code.startswith("0"):
        code = code[1:]

    # 1) BarcodeMonster API
    try:
        r = requests.get(f"https://barcode.monster/api/{code}?json=1",
                         headers=headers, timeout=3)
        if r.status_code == 200 and r.json().get("product"):
            d = r.json()
            return {
                "title":       d.get("product"),
                "brand":       d.get("brand"),
                "description": d.get("description") or d.get("product"),
                "category":    d.get("category")
            }
    except Exception:
        pass

    # 2) UPCitemdb API
    try:
        r = requests.get("https://api.upcitemdb.com/prod/trial/lookup",
                         params={"upc": code}, headers=headers, timeout=3)
        items = r.json().get("items", [])
        if items:
            item = items[0]
            return {
                "title":       item.get("title") or item.get("model"),
                "brand":       item.get("brand"),
                "description": item.get("description") or item.get("title"),
                "category":    item.get("category")
            }
    except Exception:
        pass

    # 3) OpenFoodFacts API
    try:
        r = requests.get(
            f"https://world.openfoodfacts.org/api/v0/product/{code}.json",
            headers=headers, timeout=3
        )
        data = r.json()
        if data.get("status") == 1:
            prod = data["product"]
            return {
                "title":       prod.get("product_name"),
                "brand":       prod.get("brands"),
                "description": prod.get("generic_name") or prod.get("product_name"),
                "category":    prod.get("categories") or ", ".join(prod.get("categories_tags", []))
            }
    except Exception:
        pass

    # 4) BarcodeLookup.com API
    try:
        r = requests.get("https://api.barcodelookup.com/v3/products",
                         params={
                            "barcode":   code,
                            "formatted": "n",
                            "key":       "fd2o5q9rq1x5w0b3atgq0fz3nzxq3h"
                         }, headers=headers, timeout=3)
        prods = r.json().get("products", [])
        if prods:
            p = prods[0]
            return {
                "title":       p.get("title"),
                "brand":       p.get("brand"),
                "description": p.get("description") or p.get("title"),
                "category":    p.get("category")
            }
    except Exception:
        pass

    # 5) Google Shopping via SerpAPI
    try:
        r = requests.get("https://serpapi.com/search",
                         params={
                            "engine":   "google_shopping",
                            "q":        code,
                            "api_key":  "cb63db8d1…36f00"
                         }, headers=headers, timeout=3)
        results = r.json().get("shopping_results", [])
        if results:
            res = results[0]
            return {
                "title":       res.get("title"),
                "brand":       res.get("source"),
                "description": res.get("description"),
                "category":    res.get("category")
            }
    except Exception:
        pass

    # Fallback
    return {"title": None, "brand": None, "description": None, "category": None}

def main():
    log_path = "barcodes.json"
    # Load existing log or initialize
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            records = json.load(f)
    else:
        records = []
    seen = {r["code"] for r in records}

    # Open webcam (try DirectShow on Windows)
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Cannot open camera—check index or permissions")
        return

    detector = cv2.barcode_BarcodeDetector()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            ok, decoded_info, decoded_type, corners = detector.detectAndDecodeWithType(frame)
            if ok:
                for code, btype, pts in zip(decoded_info, decoded_type, corners):
                    # skip empty, already seen
                    if not code or code in seen:
                        continue

                    # --- checksum validation ---
                    if btype == "UPC_A":
                        if not validate_upca(code):
                            continue
                    elif btype in ("EAN_8", "EAN_13"):
                        if not validate_ean_generic(code):
                            continue
                    else:
                        # ignore other barcode types
                        continue

                    # draw box + overlay text
                    draw_bbox(frame, pts)
                    x, y = pts[0].astype(int)
                    cv2.putText(
                        frame,
                        f"{code} ({btype})",
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

                    # lookup metadata
                    info = lookup_barcode(code)
                    # skip if lookup returned nothing
                    if not any(info.values()):
                        continue

                    # record and save
                    rec = {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "type":      btype,
                        "code":      code,
                        **info
                    }
                    records.append(rec)
                    seen.add(code)
                    with open(log_path, "w", encoding="utf-8") as f:
                        json.dump(records, f, indent=2, ensure_ascii=False)

            cv2.imshow("Barcode Scanner — press 'q' to quit", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

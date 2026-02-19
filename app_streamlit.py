from pathlib import Path
import json

import cv2
import numpy as np
import pandas as pd
import streamlit as st

from perception.detector import Detector
from robot.main import DobotController
from utils.camera import Camera
from utils.map import pixel_to_robot


ROOT = Path(__file__).resolve().parent
DEFAULT_IMAGE = ROOT / "outputs" / "camera_detection.png"
CALIBRATION_CANDIDATES = [
    ROOT / "calibration.json",
    ROOT / "callibration.json",
    ROOT / "calibration" / "calibration.json",
    ROOT / "calibration" / "callibration.json",
]


def _load_image(uploaded_file, captured_image):
    if uploaded_file is not None:
        data = np.frombuffer(uploaded_file.read(), np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)

    if captured_image is not None:
        return captured_image

    if DEFAULT_IMAGE.exists():
        return cv2.imread(str(DEFAULT_IMAGE))

    return None


def _load_homography(calibration_upload):
    if calibration_upload is not None:
        try:
            data = json.loads(calibration_upload.read().decode("utf-8"))
            H = data.get("homography") or data.get("homography_matrix")
            if H is None:
                return None, "Uploaded calibration JSON missing 'homography' or 'homography_matrix'"
            return np.array(H, dtype=np.float64), "Loaded calibration from uploaded file"
        except Exception as e:
            return None, f"Failed to read uploaded calibration: {e}"

    for path in CALIBRATION_CANDIDATES:
        if not path.exists():
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            H = data.get("homography") or data.get("homography_matrix")
            if H is None:
                return None, f"Calibration file found at {path.name}, but no homography key"
            return np.array(H, dtype=np.float64), f"Loaded calibration from {path}"
        except Exception as e:
            return None, f"Failed to load calibration from {path}: {e}"

    return None, "Calibration file not found"


def _to_rgb(image_bgr):
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)


def _build_rows(detected_objects, H):
    rows = []
    for idx, obj in enumerate(detected_objects, start=1):
        u, v = obj["pixel_center"]

        rx, ry = None, None
        if H is not None:
            try:
                rx, ry = pixel_to_robot(u, v, H)
                rx = float(rx)
                ry = float(ry)
            except Exception:
                rx, ry = None, None

        rows.append(
            {
                "id": idx,
                "shape": obj.get("Shape", "unknown"),
                "color": obj.get("color", "unknown"),
                "pixel_u": u,
                "pixel_v": v,
                "robot_x": rx,
                "robot_y": ry,
            }
        )

    return rows


def _annotate_image(image_bgr, rows):
    annotated = image_bgr.copy()

    for row in rows:
        u = int(row["pixel_u"])
        v = int(row["pixel_v"])
        cv2.circle(annotated, (u, v), 7, (0, 0, 255), 2)

        label = f"#{row['id']} {row['shape']}"
        if row["robot_x"] is not None and row["robot_y"] is not None:
            label += f" ({row['robot_x']:.1f}, {row['robot_y']:.1f})"

        cv2.putText(
            annotated,
            label,
            (u + 10, v - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 0, 0),
            2,
            cv2.LINE_AA,
        )

    return annotated


def _ensure_state():
    if "robot" not in st.session_state:
        st.session_state.robot = None
    if "detections" not in st.session_state:
        st.session_state.detections = []
    if "captured_image" not in st.session_state:
        st.session_state.captured_image = None


def _connect_robot(ip):
    if st.session_state.robot is not None:
        return
    st.session_state.robot = DobotController(ip=ip)


def _disconnect_robot():
    robot = st.session_state.robot
    if robot is None:
        return

    try:
        robot.disconnect()
    finally:
        st.session_state.robot = None


def main():
    st.set_page_config(page_title="Dobot MG400 Pick-and-Place", layout="wide")
    _ensure_state()

    st.title("Dobot MG400 Vision Pick-and-Place")

    with st.sidebar:
        st.subheader("Detection")
        uploaded_file = st.file_uploader("Upload image", type=["jpg", "jpeg", "png"])
        calibration_upload = st.file_uploader("Upload calibration JSON (optional)", type=["json"])
        camera_index = st.number_input("Camera Index", value=0, step=1, min_value=0)
        capture_clicked = st.button("Capture From Camera")

        if capture_clicked:
            with st.spinner("Capturing frame from camera..."):
                try:
                    camera = Camera(index=int(camera_index))
                    camera.get_frame()
                    captured = cv2.imread(str(DEFAULT_IMAGE)) if DEFAULT_IMAGE.exists() else None
                    if captured is None:
                        st.error("Camera capture failed. No image was saved.")
                    else:
                        st.session_state.captured_image = captured
                        st.session_state.detections = []
                        st.success("Captured image from camera")
                except Exception as e:
                    st.error(f"Camera capture failed: {e}")

        color_name = st.selectbox("Color", ["any", "red", "green", "blue"])
        shape_type = st.selectbox("Shape", ["any", "circle", "square"])

        st.subheader("Robot")
        robot_ip = st.text_input("Robot IP", value="192.168.1.6")
        drop_x = st.number_input("Drop X", value=275.0, step=1.0)
        drop_y = st.number_input("Drop Y", value=-125.0, step=1.0)
        drop_z = st.number_input("Drop Z", value=-75.0, step=1.0)

        col1, col2 = st.columns(2)
        with col1:
            connect_clicked = st.button("Connect")
        with col2:
            disconnect_clicked = st.button("Disconnect")

        if connect_clicked:
            with st.spinner("Connecting to robot..."):
                try:
                    _connect_robot(robot_ip)
                    st.success("Robot connected")
                except Exception as e:
                    st.error(f"Connection failed: {e}")

        if disconnect_clicked:
            with st.spinner("Disconnecting robot..."):
                try:
                    _disconnect_robot()
                    st.success("Robot disconnected")
                except Exception as e:
                    st.error(f"Disconnect failed: {e}")

    image = _load_image(uploaded_file, st.session_state.captured_image)
    if image is None:
        st.warning(
            "Upload an image, click Capture From Camera, or place `outputs/camera_detection.png` in the project root output folder."
        )
        return

    H, calibration_message = _load_homography(calibration_upload)
    if H is None:
        st.warning(f"Calibration unavailable: {calibration_message}")
    else:
        st.success(calibration_message)

    detector = Detector()

    if st.button("Detect Objects", type="primary"):
        detections = detector.find_objects(image, color_name=color_name, shape_type=shape_type)
        st.session_state.detections = _build_rows(detections, H)

    detections = st.session_state.detections

    left, right = st.columns([3, 2])

    with left:
        if detections:
            annotated = _annotate_image(image, detections)
            st.image(_to_rgb(annotated), caption="Detections", use_container_width=True)
        else:
            st.image(_to_rgb(image), caption="Input Image", use_container_width=True)

    with right:
        st.subheader("Detected Objects")

        if not detections:
            st.write("Run detection to list objects.")
            return

        df = pd.DataFrame(detections)
        st.dataframe(df, use_container_width=True)

        selectable_ids = [row["id"] for row in detections if row["robot_x"] is not None and row["robot_y"] is not None]
        if not selectable_ids:
            st.warning("No calibrated robot coordinates available for detected objects.")
            return

        selected_id = st.selectbox("Select object to pick", selectable_ids)

        robot = st.session_state.robot
        if robot is not None:
            robot.drop_location = [drop_x, drop_y, drop_z]

        pick_col1, pick_col2 = st.columns(2)

        with pick_col1:
            if st.button("Pick Selected", use_container_width=True):
                if robot is None:
                    st.error("Connect robot first")
                else:
                    row = next((r for r in detections if r["id"] == selected_id), None)
                    if row is None:
                        st.error("Selected object not found")
                    elif row["robot_x"] is None or row["robot_y"] is None:
                        st.error("Selected object has no robot coordinates")
                    else:
                        with st.spinner("Executing pick and place..."):
                            try:
                                robot.pick_and_place(row["robot_x"], row["robot_y"])
                                st.success(f"Picked object #{selected_id}")
                            except Exception as e:
                                st.error(f"Pick failed: {e}")

        with pick_col2:
            if st.button("Pick All", use_container_width=True):
                if robot is None:
                    st.error("Connect robot first")
                else:
                    with st.spinner("Executing pick and place for all objects..."):
                        try:
                            count = 0
                            for row in detections:
                                if row["robot_x"] is None or row["robot_y"] is None:
                                    continue
                                robot.pick_and_place(row["robot_x"], row["robot_y"])
                                count += 1
                            st.success(f"Completed pick-and-place for {count} object(s)")
                        except Exception as e:
                            st.error(f"Pick-all failed: {e}")


if __name__ == "__main__":
    main()

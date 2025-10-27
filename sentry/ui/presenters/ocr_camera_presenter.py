class OCRCameraPresenter:
    def __init__(self, view, camera_service, ocr_service):
        self.view = view
        self.camera = camera_service
        self.ocr = ocr_service

    def start_camera(self):
        frame = self.camera.capture_frame()
        plate_text = self.ocr.recognize(frame)
        self.view.display_plate(plate_text)

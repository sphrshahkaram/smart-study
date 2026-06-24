#!/usr/bin/env python3


import cv2
import time
import threading

try:
    import pyttsx3
    TTS_OK = True
except ImportError:
    TTS_OK = False
    print("⚠️  pip install pyttsx3")

ENCOURAGE = [
    "good job , keep going until u go to MSU",
    "great! keep going ,u smartass  !",
    "damnnnnn! its going to workout!",
    " 15 more minutes and u are smarter!",
]
STUDY_ENC_EVERY = 600   
NO_FACE_TIMEOUT = 3.0   

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Speaker:
    def __init__(self):
        self.eng = None
        self._q  = []
        self._lk = threading.Lock()
        if TTS_OK:
            try:
                self.eng = pyttsx3.init()
                self.eng.setProperty('rate', 155)
                threading.Thread(target=self._run, daemon=True).start()
            except: pass

    def say(self, text):
        print(f"🔊 {text}")
        if self.eng:
            with self._lk:
                self._q = [text]

    def _run(self):
        while True:
            msg = None
            with self._lk:
                if self._q:
                    msg = self._q.pop(0)
            if msg:
                try:
                    self.eng.say(msg)
                    self.eng.runAndWait()
                except: pass
            else:
                time.sleep(0.2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class StudyMonitor:
    def __init__(self):
        self.sp = Speaker()

        cascade = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade)

        self.session_start  = time.time()
        self.total_study    = 0.0
        self.total_away     = 0.0

        self.studying       = False
        self.state_since    = time.time()
        self.last_face_time = time.time()

        self.last_enc       = 0
        self.enc_idx        = 0

    def fmt(self, s):
        s = int(s)
        h, m, sec = s//3600, (s%3600)//60, s%60
        return f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"

    def study_time(self):
        t = self.total_study
        if self.studying:
            t += time.time() - self.state_since
        return t

    def away_time(self):
        t = self.total_away
        if not self.studying:
            t += time.time() - self.state_since
        return t

    def update(self, face_found):
        now = time.time()
        if face_found:
            self.last_face_time = now

        face_present = (now - self.last_face_time) < NO_FACE_TIMEOUT

        if face_present and not self.studying:
            # شروع مطالعه
            self.total_away += now - self.state_since
            self.studying    = True
            self.state_since = now
            self.sp.say("welcome ! ill start a timer !")

        elif not face_present and self.studying:
            # توقف مطالعه
            self.total_study += now - self.state_since
            self.studying     = False
            self.state_since  = now
            self.sp.say("u gone??? come back to build yourself a future!")

        # تشویق هر ۱۰ دقیقه
        if self.studying and now - self.last_enc >= STUDY_ENC_EVERY:
            mins = int(self.study_time() / 60)
            self.sp.say(f"good job you studied for! {mins}   !")
            self.last_enc = now

    def run(self):
        print("\n========================================")
        print("  👁️  Study Monitor")
        print("========================================\n")

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ camera not found !")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.sp.say("! hi im ready  !")

        fc = 0
        faces = []

        while True:
            ret, frame = cap.read()
            if not ret: break
            frame = cv2.flip(frame, 1)
            fc += 1

            # هر ۳ فریم تشخیص چهره
            if fc % 3 == 0:
                gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.15, minNeighbors=5, minSize=(60,60)
                )
                self.update(len(faces) > 0)

            # ── UI ──
            h, w = frame.shape[:2]

            if self.studying:
                color, label = (20, 200, 70), "STUDYING"
            else:
                color, label = (0, 180, 220), "AWAY - PAUSED"

            # رسم چهره
            for (fx, fy, fw, fh) in faces:
                cv2.rectangle(frame, (fx,fy), (fx+fw,fy+fh), (0,255,120), 2)

            # نوار بالا
            ov = frame.copy()
            cv2.rectangle(ov, (0,0), (w,75), (12,12,20), -1)
            cv2.addWeighted(ov, 0.82, frame, 0.18, 0, frame)
            cv2.rectangle(frame, (0,0), (w,5), color, -1)
            cv2.putText(frame, label, (15,52),
                        cv2.FONT_HERSHEY_DUPLEX, 1.2, color, 2, cv2.LINE_AA)

            # نوار پایین
            py = h - 100
            ov2 = frame.copy()
            cv2.rectangle(ov2, (0,py),(w,h),(12,12,20),-1)
            cv2.addWeighted(ov2, 0.85, frame, 0.15, 0, frame)
            cv2.line(frame, (0,py),(w,py),(45,45,65),1)

            cw = w // 3
            stats = [
                ("Study Time", self.fmt(self.study_time()), (30,210,90)),
                ("Away Time",  self.fmt(self.away_time()),  (0,200,220)),
                ("Session",    self.fmt(time.time()-self.session_start), (150,150,150)),
            ]
            for i,(lbl,val,c) in enumerate(stats):
                x = i*cw + 15
                cv2.putText(frame, lbl, (x, py+28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.52, (130,130,150), 1)
                cv2.putText(frame, val, (x, py+72),
                            cv2.FONT_HERSHEY_DUPLEX, 1.0, c, 2, cv2.LINE_AA)

            cv2.putText(frame, "Q=Quit  R=Reset", (w-185, py+28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (60,60,80), 1)

            cv2.imshow("Study Monitor", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27): break
            elif key == ord('r'):
                self.total_study = self.total_away = 0.0
                self.session_start = self.state_since = time.time()
                self.last_enc = 0
                print("🔄 reset")

         
        st, at = self.study_time(), self.away_time()
        total = st + at
        print("\n========================================")
        print("📊 summery:")
        print(f"  ✅ study times  : {self.fmt(st)}")
        print(f"  🚶 absence    : {self.fmt(at)}")
        if total > 0:
            print(f"  🎯 Productivity : {st/total*100:.0f}%")
        print("========================================")

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    StudyMonitor().run()

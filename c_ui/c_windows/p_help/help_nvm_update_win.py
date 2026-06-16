
import os
import sys
import json
import ftplib
import zipfile
import tempfile
import shutil
import subprocess
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QScrollArea, QFrame, QMessageBox,
    QProgressDialog, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal

from b_core.a_define import file_folder_path as path_def

# FTP 서버 정보 및 파일 설정
FTP_HOST = "121.175.173.236"
FTP_PORT = 10021
FTP_USER = "novasen"
FTP_PASS = "nova1002"
FTP_VERSION_FILE = "HDD1/NVM2App/version_info.txt"
# 배포파일 명명 규칙 (예: NVM2App_20260616-v0.0.2.zip)
FTP_ZIP_FORMAT = "HDD1/NVM2App/binary/{version}.zip"


class VersionLoadWorker(QThread):
    """
    FTP 서버에 비동기로 접속하여 version_info.txt 파일을 로드하는 스레드입니다.
    """
    sig_loaded = Signal(str)
    sig_failed = Signal(str)

    def __init__(self, ftp_host, ftp_port, ftp_user, ftp_pass):
        super().__init__()
        self.ftp_host = ftp_host
        self.ftp_port = ftp_port
        self.ftp_user = ftp_user
        self.ftp_pass = ftp_pass

    def run(self):
        try:
            ftp = ftplib.FTP()
            ftp.connect(self.ftp_host, self.ftp_port, timeout=5)
            ftp.login(self.ftp_user, self.ftp_pass)
            
            data_bytes = []
            # 파일 읽기
            ftp.retrbinary(f"RETR {FTP_VERSION_FILE}", data_bytes.append)
            ftp.quit()
            
            # UTF-8 또는 CP949 디코딩 처리
            content = b"".join(data_bytes)
            try:
                decoded = content.decode("utf-8")
            except UnicodeDecodeError:
                decoded = content.decode("cp949")
                
            self.sig_loaded.emit(decoded)
        except Exception as e:
            self.sig_failed.emit(str(e))


class FileDownloadWorker(QThread):
    """
    FTP 서버로부터 배포 파일(.zip)을 비동기로 다운로드하는 스레드입니다.
    """
    sig_progress = Signal(int, int)  # (downloaded_bytes, total_bytes)
    sig_finished = Signal(str)      # local_zip_path
    sig_failed = Signal(str)

    def __init__(self, ftp_host, ftp_port, ftp_user, ftp_pass, ftp_file_path, local_save_path):
        super().__init__()
        self.ftp_host = ftp_host
        self.ftp_port = ftp_port
        self.ftp_user = ftp_user
        self.ftp_pass = ftp_pass
        self.ftp_file_path = ftp_file_path
        self.local_save_path = local_save_path
        self.is_canceled = False

    def run(self):
        ftp = None
        try:
            ftp = ftplib.FTP()
            ftp.connect(self.ftp_host, self.ftp_port, timeout=10)
            ftp.login(self.ftp_user, self.ftp_pass)
            
            # 바이너리 모드로 전환 (SIZE 명령어는 바이너리 모드에서 규격 준수됨)
            try:
                ftp.voidcmd('TYPE I')
            except Exception:
                pass

            # 전체 파일 크기 가져오기
            try:
                total_bytes = ftp.size(self.ftp_file_path)
            except Exception:
                total_bytes = 0

            downloaded_bytes = 0
            
            with open(self.local_save_path, "wb") as f:
                def callback(block):
                    nonlocal downloaded_bytes
                    if self.is_canceled:
                        raise InterruptedError("Download canceled by user")
                    f.write(block)
                    downloaded_bytes += len(block)
                    self.sig_progress.emit(downloaded_bytes, total_bytes)
                
                ftp.retrbinary(f"RETR {self.ftp_file_path}", callback, blocksize=8192)
            
            ftp.quit()
            if not self.is_canceled:
                self.sig_finished.emit(self.local_save_path)
        except Exception as e:
            # 다운로드 도중 실패 시 로컬 임시파일 삭제
            if os.path.exists(self.local_save_path):
                try:
                    os.remove(self.local_save_path)
                except Exception:
                    pass
            if not self.is_canceled:
                self.sig_failed.emit(str(e))
            else:
                self.sig_failed.emit("CANCELED")
        finally:
            if ftp:
                try:
                    ftp.close()
                except Exception:
                    pass

    def cancel(self):
        self.is_canceled = True

class HelpNvmUpdateWin(QMainWindow):
    """
    NVM2App의 버젼 정보를 표시하고 업데이트할 수 있는 도움말 업데이트 창입니다.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NVM Update")
        self.resize(500, 600)
        
        self.download_worker = None
        self.progress_dialog = None
        self.load_ftp_info()
        self.init_ui()
        self.start_load_version_info()

    def load_ftp_info(self):
        # 기본값 셋업
        self.ftp_host = FTP_HOST
        self.ftp_port = FTP_PORT
        self.ftp_user = FTP_USER
        self.ftp_pass = FTP_PASS

        if os.path.exists(path_def.RSRC_FTP_SETTING_FILE):
            try:
                with open(path_def.RSRC_FTP_SETTING_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                self.ftp_host = config.get("FTP_HOST", self.ftp_host)
                
                # 포트 정수 변환 처리
                port_val = config.get("FTP_PORT", self.ftp_port)
                try:
                    self.ftp_port = int(port_val)
                except ValueError:
                    pass
                    
                #self.ftp_user = config.get("FTP_USER", self.ftp_user)
                #self.ftp_pass = config.get("FTP_PASS", self.ftp_pass)
                
                #print(f"Loaded FTP settings from JSON {path_def.RSRC_FTP_SETTING_FILE}: {self.ftp_host}:{self.ftp_port}")
            except Exception as e:
                print(f"Error loading FTP JSON info: {e}")
        else:
            print("FTP JSON info file not found, using default credentials")

    def init_ui(self):
        # 메인 센트럴 위젯 및 레이아웃
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        # 상단 타이틀 안내문구
        self.title_label = QLabel("NVM2App 업데이트 이력 및 설치", self)
        title_font = self.title_label.font()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #202124;")
        self.main_layout.addWidget(self.title_label)

        # 상태 및 알림 라벨
        self.status_label = QLabel("서버에서 업데이트 정보를 로드하고 있습니다...", self)
        self.status_label.setStyleSheet("color: #5f6368; font-size: 11px;")
        self.main_layout.addWidget(self.status_label)

        # 스크롤 영역 설정 (리스트 전체가 통으로 나오도록 함)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #dadce0;
                border-radius: 6px;
                background-color: #ffffff;
            }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setContentsMargins(15, 15, 15, 15)
        self.scroll_layout.setSpacing(20)
        self.scroll_area.setWidget(self.scroll_content)
        
        self.main_layout.addWidget(self.scroll_area)

        # 하단 닫기 버튼 레이아웃
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        self.close_btn = QPushButton("닫기", self)
        self.close_btn.setMinimumWidth(80)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f3f4;
                color: #3c4043;
                border: 1px solid #dadce0;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e8eaed;
            }
            QPushButton:pressed {
                background-color: #dadce0;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(self.close_btn)
        
        self.main_layout.addLayout(bottom_layout)

    def start_load_version_info(self):
        """
        비동기 작업자를 시작하여 FTP 서버에서 버전 정보를 가져옵니다.
        """
        self.load_worker = VersionLoadWorker(self.ftp_host, self.ftp_port, self.ftp_user, self.ftp_pass)
        self.load_worker.sig_loaded.connect(self.on_version_loaded)
        self.load_worker.sig_failed.connect(self.on_version_load_failed)
        self.load_worker.start()

    def on_version_loaded(self, content):
        """
        FTP 버전 로드가 성공했을 때의 콜백입니다.
        """
        self.status_label.setText("업데이트 정보가 FTP 서버로부터 최신화되었습니다.")
        self.status_label.setStyleSheet("color: #1e8e3e; font-size: 11px;")
        versions = self.parse_version_info(content)
        self.populate_version_list(versions)

    def on_version_load_failed(self, error_msg):
        """
        FTP 버전 로드가 실패했을 때(예: 오프라인)의 콜백입니다.
        로컬 version_info.txt 탐색 또는 하드코딩 폴백 데이터로 작동합니다.
        """
        self.status_label.setText("서버 연결 실패. (로컬 폴백 데이터를 표시합니다)")
        self.status_label.setStyleSheet("color: #d93025; font-size: 11px;")
        
        # 로컬 폴백 파일 탐색
        possible_paths = [
            os.path.join(os.getcwd(), "version_info.txt"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "version_info.txt")),
            os.path.join(os.path.dirname(os.getcwd()), "version_info.txt")
        ]
        
        content = None
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    break
                except Exception:
                    pass
        
        if not content:
            content = """
[VER : 20260616-v0.0.2]
1. 업데이트 기능 수정
2. 버튼 이미지 수정
-------------------------------------------------------------------
[VER : 20260610-v0.0.1]
1. 최초 버젼 (NV2 프로토콜 전용 앱)
-------------------------------------------------------------------
"""
        versions = self.parse_version_info(content)
        self.populate_version_list(versions)

    def populate_version_list(self, versions):
        """
        파싱된 버전을 바탕으로 GUI 카드를 동적 렌더링합니다.
        """
        # 기존 스크롤 내부 위젯 초기화
        for i in reversed(range(self.scroll_layout.count())): 
            widget = self.scroll_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        for idx, item in enumerate(versions):
            card_widget = QWidget()
            card_layout = QVBoxLayout(card_widget)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(8)

            # 1. 헤더 레이아웃 (버전 이름 + 업데이트 버튼)
            header_layout = QHBoxLayout()
            
            ver_label = QLabel(f"[VER : {item['version']}]")
            ver_font = ver_label.font()
            ver_font.setBold(True)
            ver_font.setPointSize(11)
            ver_label.setFont(ver_font)
            ver_label.setStyleSheet("color: #1a73e8;")
            header_layout.addWidget(ver_label)
            
            header_layout.addStretch()
            
            update_btn = QPushButton("업데이트")
            update_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1a73e8;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 14px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #1557b0;
                }
                QPushButton:pressed {
                    background-color: #0b3c80;
                }
            """)
            update_btn.clicked.connect(lambda checked=False, v=item['version']: self.on_clicked_update(v))
            header_layout.addWidget(update_btn)
            
            card_layout.addLayout(header_layout)

            # 2. 수정내용 (Release Notes)
            notes_label = QLabel(item['release_notes'])
            notes_label.setWordWrap(True)
            notes_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            notes_label.setStyleSheet("""
                QLabel {
                    color: #3c4043;
                    font-size: 12px;
                    line-height: 1.5;
                    padding-left: 5px;
                }
            """)
            card_layout.addWidget(notes_label)

            self.scroll_layout.addWidget(card_widget)

            # 마지막 항목이 아닐 경우 구분선 추가
            if idx < len(versions) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                line.setStyleSheet("color: #dadce0; margin-top: 10px; margin-bottom: 10px;")
                self.scroll_layout.addWidget(line)

    def parse_version_info(self, content):
        """
        version_info.txt 텍스트 파일 포멧을 파싱합니다.
        """
        versions = []
        current_ver = None
        current_notes = []

        for line in content.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            
            # [VER : 버전명] 감지
            if line_str.startswith("[VER :") and line_str.endswith("]"):
                if current_ver:
                    versions.append({
                        "version": current_ver,
                        "release_notes": "\n".join(current_notes).strip()
                    })
                current_ver = line_str[6:-1].strip()
                current_notes = []
            # 구분선 감지 시 현재 파싱 중인 버전 저장 및 리셋
            elif line_str.startswith("-----"):
                if current_ver:
                    versions.append({
                        "version": current_ver,
                        "release_notes": "\n".join(current_notes).strip()
                    })
                    current_ver = None
                    current_notes = []
            else:
                if current_ver:
                    current_notes.append(line)

        # 마지막 처리되지 않은 버전 정보 추가
        if current_ver:
            versions.append({
                "version": current_ver,
                "release_notes": "\n".join(current_notes).strip()
            })

        return versions

    def on_clicked_update(self, version_name):
        """
        [업데이트] 버튼 클릭 시 해당 버전 배포 파일 다운로드 및 실행 파일 패치를 시작합니다.
        """
        reply = QMessageBox.question(
            self, "업데이트 시작",
            f"선택하신 버전 {version_name}으로 업데이트를 진행하시겠습니까?\n업데이트가 완료되면 프로그램이 자동으로 재시작됩니다.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        ftp_file_path = FTP_ZIP_FORMAT.format(version=version_name)
        local_zip_path = os.path.join(tempfile.gettempdir(), f"NVM2App_update_{version_name}.zip")

        # 진행 표시창 설정
        self.progress_dialog = QProgressDialog("배포 파일을 다운로드하는 중...", "취소", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setWindowTitle("NVM App Update")
        self.progress_dialog.setMinimumDuration(0)  # 딜레이 없이 즉시 노출 설정
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()                 # 명시적으로 다이얼로그 띄움
        self.progress_dialog.canceled.connect(self.on_download_canceled)

        # 백그라운드 다운로드 스레드 구동
        self.download_worker = FileDownloadWorker(
            self.ftp_host, self.ftp_port, self.ftp_user, self.ftp_pass,
            ftp_file_path, local_zip_path
        )
        self.download_worker.sig_progress.connect(self.on_download_progress)
        self.download_worker.sig_finished.connect(lambda p: self.on_download_finished(p, version_name))
        self.download_worker.sig_failed.connect(self.on_download_failed)
        self.download_worker.start()

    def on_download_progress(self, downloaded, total):
        """
        다운로드 진행률 이벤트 수신 및 다이얼로그 업데이트
        """

        if total > 0:
            percentage = int((downloaded / total) * 100)

            self.progress_dialog.setValue(percentage)
            self.progress_dialog.setLabelText(
                f"배포 파일 다운로드 중... ({percentage}%) \n"
                f"[{downloaded // 1024} KB / {total // 1024} KB]"
            )
        else:
            self.progress_dialog.setLabelText(f"배포 파일 다운로드 중... ({downloaded // 1024} KB)")

    def on_download_canceled(self):
        """
        사용자가 다운로드 취소 클릭 시 스레드 중단
        """
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.cancel()

    def on_download_failed(self, error_msg):
        """
        다운로드 실패 또는 취소 시 콜백
        """
        if self.progress_dialog:
            self.progress_dialog.close()
        
        if error_msg == "CANCELED":
            QMessageBox.information(self, "업데이트 취소", "다운로드가 사용자에 의해 취소되었습니다.")
        else:
            QMessageBox.critical(
                self, "업데이트 오류",
                f"배포 파일을 다운로드하지 못했습니다.\n\n[에러 내역]\n{error_msg}"
            )

    def on_download_finished(self, zip_path, version_name):
        """
        다운로드 성공 시 호출되어 압축 풀기 및 update.bat 자가 교체 스크립트를 기동합니다.
        """
        if self.progress_dialog:
            self.progress_dialog.close()

        # 임시 압축 해제 디렉토리
        extract_dir = os.path.join(tempfile.gettempdir(), f"NVM2App_extracted_{version_name}")
        if os.path.exists(extract_dir):
            try:
                shutil.rmtree(extract_dir)
            except Exception:
                pass
        os.makedirs(extract_dir, exist_ok=True)

        try:
            # 1. 압축 해제
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
        except Exception as e:
            QMessageBox.critical(self, "압축 해제 오류", f"다운로드된 배포 파일의 압축을 해제하지 못했습니다.\n{str(e)}")
            return

        # 2. 프로그램 실행 디렉토리 및 실행 파일명 획득
        if getattr(sys, 'frozen', False):
            current_app_dir = os.path.dirname(sys.executable)
            exe_name = os.path.basename(sys.executable)
        else:
            current_app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            exe_name = os.path.basename(sys.argv[0])

        # 3. 업데이트 배치 파일 생성
        bat_path = os.path.join(tempfile.gettempdir(), "nvm_app_update.bat")
        
        bat_content = f"""@echo off
setlocal
chcp 65001 > nul
echo -------------------------------------------------------------
echo NVM2App 자동 업데이트 진행 중... 잠시만 기다려 주십시오.
echo -------------------------------------------------------------
timeout /t 2 /nobreak > nul

set retry_count=0

:wait_lock
ren "{current_app_dir}\\{exe_name}" "{exe_name}_tmp_lock_test" > nul 2>&1
if errorlevel 1 (
    set /a retry_count+=1
    if %retry_count% gtr 10 (
        echo [에러] 파일 교체 실패: 기존 프로그램이 종료되지 않았거나 잠겨 있습니다.
        pause
        exit /b 1
    )
    echo 기존 프로그램의 종료를 기다리는 중...
    timeout /t 1 /nobreak > nul
    goto wait_lock
)

ren "{current_app_dir}\\{exe_name}_tmp_lock_test" "{exe_name}" > nul 2>&1

:: 안전하게 구버전 위에 새 버전 덮어쓰기 복사
xcopy "{extract_dir}\\*.*" "{current_app_dir}\\" /y /e /q

:: [★ 초핵심 수정 1] 백신(Windows Defender) 스캔 및 디스크 캐시가 완전히 풀릴 시간을 줍니다.
echo -------------------------------------------------------------
echo 시스템 안정화를 위해 잠시 대기합니다 (백신 스캔 및 디스크 동기화)...
echo -------------------------------------------------------------
timeout /t 5 /nobreak > nul

echo 업데이트 완료! 애플리케이션을 다시 시작합니다.

:: [★ 초핵심 수정 2] 윈도우 탐색기(explorer.exe)를 통해 앱을 실행합니다.
:: 명령 프롬프트가 실행하는 게 아니라, 윈도우 쉘 시스템이 사용자의 '마우스 더블클릭' 액션을 그대로 모사하여 실행합니다.
explorer.exe "{current_app_dir}\\{exe_name}"

:: 임시 추출 폴더 정리
rmdir /s /q "{extract_dir}"
:: 배치 파일 자가 삭제
del "%~f0"
"""
        try:
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
        except Exception as e:
            QMessageBox.critical(self, "패치 실패", f"업데이트 스크립트를 생성하지 못했습니다.\n{str(e)}")
            return

        # 4. 환경 변수를 완전히 비운 깨끗한 세션으로 배치 파일 기동
        try:
            clean_env = os.environ.copy()
            clean_env.pop('_MEIPASS', None)
            clean_env.pop('PYI_PARENT_ADDR', None)
            clean_env.pop('PYI_CHILD_FLAG', None)

            subprocess.Popen(
                ["cmd.exe", "/c", bat_path],
                env=clean_env,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            os._exit(0)
        except Exception as e:
            QMessageBox.critical(self, "실행 실패", f"업데이트 프로세스를 시작하지 못했습니다.\n{str(e)}")
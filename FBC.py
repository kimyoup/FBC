"""
🎯 악어스튜디오 캡쳐 피드백 도구 V1.6.1 - 배포 최적화 버전
==================================================
- 영역 선택으로 다중 주석 선택/이동/삭제
- PDF 텍스트 주석 완벽 출력 (배경/테두리 제거)
- 빈 캔버스 생성 기능 추가
- UI 레이아웃 최적화
- PDF 정보 입력창 분리
- 모든 기능 디버그 및 최적화 완료

🚀 V1.6.1 배포 최적화:
- 동적 디버그 모드 (--debug 플래그 또는 DEBUG_MODE 환경변수)
- 프로덕션 로그 레벨 최적화 (WARNING 이상만 출력)
- 콘솔 창 자동 숨김 (프로덕션 모드)
- 디버그 출력 완전 제거 (프로덕션 모드)
==================================================
"""

import sys
import os
import threading
import time
import json
import io
import base64
import math
import logging
import traceback
import gc
import tempfile
import platform
import shutil
import weakref
from datetime import datetime
from pathlib import Path
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import subprocess

# 🔥 중복 제거된 모듈 import
from constants import VERSION, BUILD_DATE, COPYRIGHT
from utils import resource_path, setup_logging, setup_window_icon, create_improved_arrow

# 로깅 초기화
logger = setup_logging()

# 시스템 정보 로깅
logger.info("=" * 60)
logger.info(f"피드백 캔버스 V{VERSION}")
logger.info(f"빌드일: {BUILD_DATE}")
logger.info(f"시스템: {platform.system()} {platform.release()}")
logger.info(f"Python: {sys.version}")
logger.info("=" * 60)

# 🔥 [중복 제거됨] V1.6.1 블록 #1
# GUI 라이브러리
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog, font
    logger.info("✓ tkinter 모듈 로드 성공")
except ImportError as e:
    logger.critical(f"tkinter 모듈을 찾을 수 없습니다: {e}")
    sys.exit(1)

# 이미지 처리
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_AVAILABLE = True
    logger.info("✓ Pillow 모듈 로드 성공")
except ImportError as e:
    logger.critical(f"Pillow 모듈이 필요합니다: {e}")
    messagebox.showerror("필수 모듈 오류", 
                        "Pillow 모듈이 필요합니다.\n\n설치 방법:\n1. 명령 프롬프트(CMD)를 관리자 권한으로 실행\n2. pip install Pillow 입력\n3. 프로그램 재시작")
    sys.exit(1)

# PDF 생성
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.units import inch, mm
    REPORTLAB_AVAILABLE = True
    logger.info("✓ ReportLab 모듈 로드 성공")
except ImportError as e:
    logger.warning(f"ReportLab 모듈이 없습니다: {e}")
    REPORTLAB_AVAILABLE = False

# 화면 캡처
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.1
    PYAUTOGUI_AVAILABLE = True
    logger.info("✓ PyAutoGUI 모듈 로드 성공")
except ImportError as e:
    logger.warning(f"PyAutoGUI 모듈이 없습니다: {e}")
    PYAUTOGUI_AVAILABLE = False

# 다중 모니터 지원 캡처
try:
    import mss
    MSS_AVAILABLE = True
    logger.info("✓ MSS(다중 모니터) 모듈 로드 성공")
except ImportError as e:
    logger.warning(f"MSS 모듈이 없습니다: {e}")
    MSS_AVAILABLE = False

# Excel 내보내기
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
    logger.info("✓ Pandas 모듈 로드 성공")
except ImportError as e:
    logger.warning(f"Pandas 모듈이 없습니다: {e}")
    PANDAS_AVAILABLE = False

# 메모리 모니터링
try:
    import psutil
    PSUTIL_AVAILABLE = True
    logger.info("✓ psutil 모듈 로드 성공")
except ImportError as e:
    logger.warning(f"psutil 모듈이 없습니다: {e}")
    PSUTIL_AVAILABLE = False

# GitHub 업데이트 확인을 위한 모듈
try:
    import urllib.request
    import urllib.parse
    import json
    import ssl
    import webbrowser
    import zipfile
    import shutil
    GITHUB_UPDATE_AVAILABLE = True
    logger.info("✓ GitHub 업데이트 관련 모듈 로드 성공")
except ImportError as e:
    logger.warning(f"GitHub 업데이트 모듈 로드 실패: {e}")
    GITHUB_UPDATE_AVAILABLE = False

class SafeThreadExecutor:
    """Thread-safe 작업 실행기"""
    
    def __init__(self, max_workers=2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures = set()
        self._cleanup_completed()
    
    def submit(self, fn, *args, **kwargs):
        """작업 제출"""
        future = self.executor.submit(fn, *args, **kwargs)
        self.futures.add(future)
        return future
    
    def _cleanup_completed(self):
        """완료된 작업 정리"""
        completed = {f for f in self.futures if f.done()}
        self.futures -= completed
    
    def shutdown(self):
        """실행기 종료"""
        self.executor.shutdown(wait=False)

class SystemMonitor:
    """시스템 리소스 모니터링"""
    
    def __init__(self):
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None
        self.memory_warnings = 0
        # 🔥 웹툰 지원: 메모리 제한 대폭 증가 (1GB → 3GB)
        self.max_memory_mb = 3072  # 웹툰과 같은 큰 이미지들을 위해 3GB로 증가
        self._last_memory_check = 0
        self._memory_check_interval = 3  # 체크 간격 단축 (5초 → 3초)
    
    def get_memory_usage(self):
        """현재 메모리 사용량 반환 (MB)"""
        try:
            if self.process:
                current_time = time.time()
                if current_time - self._last_memory_check > self._memory_check_interval:
                    self._last_memory_check = current_time
                    return self.process.memory_info().rss / 1024 / 1024
                return getattr(self, '_cached_memory', 0)
            return 0
        except Exception:
            return 0
    
    def check_memory_limit(self):
        """메모리 제한 확인"""
        current_memory = self.get_memory_usage()
        self._cached_memory = current_memory
        
        if current_memory > self.max_memory_mb:
            self.memory_warnings += 1
            logger.warning(f"메모리 사용량 초과: {current_memory:.1f}MB")
            if self.memory_warnings > 3:
                return False
        return True
    
    def get_disk_space(self, path):
        """디스크 공간 확인 (MB)"""
        try:
            if PSUTIL_AVAILABLE:
                usage = psutil.disk_usage(path)
                return usage.free / 1024 / 1024
            return float('inf')
        except Exception:
            return float('inf')

class AdvancedProgressDialog:
    """향상된 진행 상황 표시 다이얼로그"""
    
    def __init__(self, parent, title, message, auto_close_ms=None, cancelable=False):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        
        # 🔥 아이콘 설정
        setup_window_icon(self.dialog)
        
        self.dialog.geometry("450x180")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.canceled = False
        self.cancel_callback = None
        
        if auto_close_ms:
            self.dialog.after(auto_close_ms, self.close)

        # 창 중앙 배치
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 225
        y = (self.dialog.winfo_screenheight() // 2) - 90
        self.dialog.geometry(f"+{x}+{y}")
        
        # UI 구성
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.message_label = tk.Label(main_frame, text=message, 
                                     font=('맑은 고딕', 11, 'bold'))
        self.message_label.pack(pady=(0, 15))
        
        # 진행률 바와 퍼센트 표시를 함께
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate', length=350)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.percent_label = tk.Label(progress_frame, text="0%", font=('맑은 고딕', 9, 'bold'), width=5)
        self.percent_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.detail_label = tk.Label(main_frame, text="", 
                                    font=('맑은 고딕', 9), fg='#666')
        self.detail_label.pack()
        
        # 취소 버튼 (옵션)
        if cancelable:
            self.cancel_btn = tk.Button(main_frame, text="취소", 
                                       command=self.cancel,
                                       bg='#dc3545', fg='white',
                                       font=('맑은 고딕', 9))
            self.cancel_btn.pack(pady=(10, 0))
        
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel if cancelable else lambda: None)
        self.dialog.update()
    
    def update(self, value, detail=""):
        """진행률 업데이트"""
        try:
            if self.canceled:
                return False
                
            self.progress['value'] = min(100, max(0, value))
            self.percent_label.config(text=f"{int(value)}%")
            
            if detail:
                self.detail_label.config(text=detail)
            self.dialog.update()
            return True
        except Exception:
            return False
    
    def cancel(self):
        """취소 처리"""
        self.canceled = True
        if self.cancel_callback:
            self.cancel_callback()
        self.close()
    
    def set_cancel_callback(self, callback):
        """취소 콜백 설정"""
        self.cancel_callback = callback
    
    def close(self):
        """다이얼로그 닫기"""
        try:
            self.dialog.destroy()
        except Exception:
            pass

class SmartUndoManager:
    """스마트 되돌리기 관리 클래스"""
    
    def __init__(self, max_history=8):
        self.max_history = max_history
        self.histories = {}
        self._last_cleanup = time.time()
    
    def save_state(self, item_id, annotations):
        """현재 주석 상태 저장"""
        try:
            if item_id not in self.histories:
                self.histories[item_id] = deque(maxlen=self.max_history)
            
            state = [ann.copy() for ann in annotations]
            self.histories[item_id].append(state)
            
            if time.time() - self._last_cleanup > 300:
                self._cleanup_old_histories()
                
            logger.debug(f"상태 저장됨 - Item {item_id}: {len(state)}개 주석")
            
        except Exception as e:
            logger.error(f"상태 저장 오류: {e}")
    
    def undo(self, item_id):
        """되돌리기 실행"""
        try:
            if item_id not in self.histories or len(self.histories[item_id]) <= 1:
                return None
            
            self.histories[item_id].pop()
            if self.histories[item_id]:
                prev_state = self.histories[item_id][-1]
                restored_state = [ann.copy() for ann in prev_state]
                
                logger.debug(f"되돌리기 실행 - Item {item_id}: {len(restored_state)}개 주석")
                return restored_state
            
            return []
            
        except Exception as e:
            logger.error(f"되돌리기 오류: {e}")
            return None
    
    def can_undo(self, item_id):
        """되돌리기 가능한지 확인"""
        return (item_id in self.histories and len(self.histories[item_id]) > 1)
    
    def _cleanup_old_histories(self):
        """오래된 히스토리 정리"""
        try:
            empty_keys = [k for k, v in self.histories.items() if not v]
            for k in empty_keys:
                del self.histories[k]
            
            self._last_cleanup = time.time()
            
        except Exception as e:
            logger.debug(f"히스토리 정리 오류: {e}")
    
    def clear_history(self, item_id):
        """특정 항목의 히스토리 초기화"""
        if item_id in self.histories:
            self.histories[item_id].clear()
    
    def clear_all(self):
        """모든 히스토리 초기화"""
        self.histories.clear()

class GitHubUpdateChecker:
    """GitHub 릴리즈 업데이트 확인 클래스"""
    
    def __init__(self, repo_owner="kimyoup", repo_name="FBC", current_version=VERSION):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.current_version = current_version
        self.api_url = f"https://api.github.com/repos/kimyoup/FBC/releases/latest"
        self.repo_url = f"https://github.com/kimyoup/FBC"
        self._cache = {}
        self._cache_time = 0
        self._cache_duration = 3600  # 1시간 캐시
    
    def check_for_updates(self):
        """새 버전 확인"""
        try:
            # 캐시 확인
            current_time = time.time()
            if (current_time - self._cache_time < self._cache_duration and 
                'latest_release' in self._cache):
                return self._cache['latest_release']
            
            logger.info(f"GitHub 업데이트 확인 중... (현재: v{self.current_version})")
            
            # SSL 컨텍스트 설정
            context = ssl.create_default_context()
            
            # GitHub API 요청
            request = urllib.request.Request(self.api_url)
            request.add_header('User-Agent', f'FeedBC-UpdateChecker/{self.current_version}')
            
            with urllib.request.urlopen(request, context=context, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            latest_version = data.get('tag_name', '').lstrip('v')
            release_name = data.get('name', '')
            release_body = data.get('body', '')
            release_url = data.get('html_url', '')
            published_at = data.get('published_at', '')
            assets = data.get('assets', [])
            
            # 다운로드 가능한 자산 찾기 (exe 파일 우선)
            download_assets = []
            exe_assets = []
            other_assets = []
            
            for asset in assets:
                asset_name = asset.get('name', '').lower()
                if asset_name.endswith('.exe'):
                    exe_assets.append({
                        'name': asset.get('name'),
                        'download_url': asset.get('browser_download_url'),
                        'size': asset.get('size', 0),
                        'type': 'exe'
                    })
                elif asset_name.endswith(('.zip', '.msi', '.tar.gz')):
                    other_assets.append({
                        'name': asset.get('name'),
                        'download_url': asset.get('browser_download_url'),
                        'size': asset.get('size', 0),
                        'type': 'archive'
                    })
            
            # exe 파일을 우선적으로 배치
            download_assets.extend(exe_assets)
            download_assets.extend(other_assets)
            
            release_info = {
                'latest_version': latest_version,
                'current_version': self.current_version,
                'has_update': self._compare_versions(latest_version, self.current_version),
                'release_name': release_name,
                'release_notes': release_body,
                'release_url': release_url,
                'published_at': published_at,
                'download_assets': download_assets
            }
            
            # 캐시 업데이트
            self._cache['latest_release'] = release_info
            self._cache_time = current_time
            
            if release_info['has_update']:
                logger.info(f"✅ 새 버전 발견: v{latest_version}")
            else:
                logger.info(f"✅ 최신 버전 사용 중: v{self.current_version}")
            
            return release_info
            
        except urllib.error.URLError as e:
            logger.warning(f"네트워크 오류로 업데이트 확인 실패: {e}")
            return {'error': '네트워크 연결을 확인해주세요'}
        except json.JSONDecodeError as e:
            logger.warning(f"GitHub API 응답 파싱 실패: {e}")
            return {'error': 'GitHub API 응답 오류'}
        except Exception as e:
            logger.error(f"업데이트 확인 중 오류: {e}")
            return {'error': f'업데이트 확인 실패: {str(e)}'}
    
    def _compare_versions(self, latest, current):
        """버전 비교 (semantic versioning 지원)"""
        try:
            def version_tuple(v):
                # v1.2.3 -> (1, 2, 3)
                parts = v.replace('v', '').split('.')
                return tuple(int(x) for x in parts if x.isdigit())
            
            latest_tuple = version_tuple(latest)
            current_tuple = version_tuple(current)
            
            return latest_tuple > current_tuple
            
        except Exception as e:
            logger.debug(f"버전 비교 오류: {e}")
            return latest != current
    
    def download_update(self, asset_url, save_path, progress_callback=None):
        """exe 업데이트 파일 다운로드"""
        try:
            logger.info(f"exe 파일 다운로드 시작: {asset_url}")
            
            # exe 파일 확장자 확인
            if not save_path.lower().endswith('.exe'):
                save_path = save_path.replace('.zip', '.exe').replace('.tar.gz', '.exe')
                if not save_path.lower().endswith('.exe'):
                    save_path += '.exe'
            
            # 다운로드 디렉토리 생성
            save_dir = Path(save_path).parent
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # 기존 파일 백업
            if Path(save_path).exists():
                backup_path = str(save_path).replace('.exe', '_backup.exe')
                if Path(backup_path).exists():
                    Path(backup_path).unlink()
                Path(save_path).rename(backup_path)
                logger.info(f"기존 exe 파일 백업: {backup_path}")
            
            context = ssl.create_default_context()
            request = urllib.request.Request(asset_url)
            request.add_header('User-Agent', f'FeedBC-UpdateChecker/{self.current_version}')
            
            with urllib.request.urlopen(request, context=context) as response:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(save_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress)
            
            # exe 파일 검증
            if Path(save_path).exists() and Path(save_path).stat().st_size > 0:
                file_size = Path(save_path).stat().st_size
                logger.info(f"✅ exe 파일 다운로드 완료: {save_path} ({file_size:,} bytes)")
                
                # exe 파일 실행 권한 확인 (Windows에서는 자동)
                if save_path.lower().endswith('.exe'):
                    logger.info("✅ 실행 가능한 exe 파일 다운로드 완료")
                
                return True
            else:
                logger.error("다운로드된 exe 파일이 비어있거나 손상됨")
                return False
            
        except Exception as e:
            logger.error(f"exe 파일 다운로드 실패: {e}")
            return False

class UpdateNotificationDialog:
    """업데이트 알림 다이얼로그"""
    
    def __init__(self, parent, update_info, update_checker):
        self.parent = parent
        self.update_info = update_info
        self.update_checker = update_checker
        self.result = None
        self.dialog = None
        
        self.create_dialog()
    
    def create_dialog(self):
        """업데이트 알림 다이얼로그 생성"""
        try:
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title("🚀 새 버전 업데이트")
            
            # 창 크기 설정
            dialog_width = 600
            dialog_height = 500
            self.dialog.geometry(f"{dialog_width}x{dialog_height}")
            self.dialog.resizable(True, True)
            self.dialog.minsize(500, 400)
            self.dialog.configure(bg='white')
            
            # 아이콘 설정
            setup_window_icon(self.dialog)
            
            # 메인 프레임
            main_frame = tk.Frame(self.dialog, bg='white')
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # 제목 섹션
            title_frame = tk.Frame(main_frame, bg='white')
            title_frame.pack(fill=tk.X, pady=(0, 20))
            
            title_label = tk.Label(title_frame, 
                                 text="🎉 새로운 버전이 출시되었습니다!",
                                 font=('맑은 고딕', 16, 'bold'),
                                 fg='#2196F3', bg='white')
            title_label.pack()
            
            # 버전 정보
            version_frame = tk.Frame(main_frame, bg='white')
            version_frame.pack(fill=tk.X, pady=(0, 15))
            
            current_label = tk.Label(version_frame, 
                                   text=f"현재 버전: v{self.update_info['current_version']}",
                                   font=('맑은 고딕', 12),
                                   fg='#666', bg='white')
            current_label.pack(anchor=tk.W)
            
            latest_label = tk.Label(version_frame, 
                                  text=f"최신 버전: v{self.update_info['latest_version']}",
                                  font=('맑은 고딕', 12, 'bold'),
                                  fg='#4CAF50', bg='white')
            latest_label.pack(anchor=tk.W)
            
            if self.update_info.get('published_at'):
                try:
                    from datetime import datetime
                    pub_date = datetime.fromisoformat(self.update_info['published_at'].replace('Z', '+00:00'))
                    date_str = pub_date.strftime('%Y년 %m월 %d일')
                    date_label = tk.Label(version_frame, 
                                        text=f"출시일: {date_str}",
                                        font=('맑은 고딕', 10),
                                        fg='#666', bg='white')
                    date_label.pack(anchor=tk.W)
                except:
                    pass
            
            # 릴리즈 노트 섹션
            notes_frame = tk.LabelFrame(main_frame, text="📋 업데이트 내용", 
                                      bg='white', font=('맑은 고딕', 11, 'bold'))
            notes_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            
            # 스크롤 가능한 텍스트 영역
            text_frame = tk.Frame(notes_frame, bg='white')
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            self.notes_text = tk.Text(text_frame, wrap=tk.WORD, 
                                    font=('맑은 고딕', 10),
                                    bg='#f8f9fa', relief='solid', bd=1)
            notes_scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, 
                                         command=self.notes_text.yview)
            self.notes_text.configure(yscrollcommand=notes_scrollbar.set)
            
            self.notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            notes_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 릴리즈 노트 내용 추가
            release_notes = self.update_info.get('release_notes', '업데이트 내용을 확인할 수 없습니다.')
            if not release_notes.strip():
                release_notes = '이번 업데이트의 자세한 내용은 GitHub 페이지에서 확인하실 수 있습니다.'
            
            self.notes_text.insert('1.0', release_notes)
            self.notes_text.config(state=tk.DISABLED)
            
            # 버튼 섹션
            button_frame = tk.Frame(main_frame, bg='white')
            button_frame.pack(fill=tk.X, pady=(10, 0))
            
            # 나중에 버튼
            later_btn = tk.Button(button_frame, text="나중에",
                                command=self.later,
                                font=('맑은 고딕', 11),
                                bg='white', fg='#666666',
                                relief='solid', bd=1,
                                padx=20, pady=8)
            later_btn.pack(side=tk.LEFT)
            
            # GitHub에서 보기 버튼
            github_btn = tk.Button(button_frame, text="📱 GitHub에서 보기",
                                 command=self.open_github,
                                 font=('맑은 고딕', 11),
                                 bg='white', fg='#6f42c1',
                                 relief='solid', bd=1,
                                 padx=20, pady=8)
            github_btn.pack(side=tk.RIGHT, padx=(10, 0))
            
            # 다운로드 버튼 (다운로드 가능한 자산이 있는 경우)
            if self.update_info.get('download_assets'):
                download_btn = tk.Button(button_frame, text="🔽 다운로드",
                                       command=self.download_update,
                                       font=('맑은 고딕', 11, 'bold'),
                                       bg='#4CAF50', fg='white',
                                       relief='solid', bd=1,
                                       padx=25, pady=8)
                download_btn.pack(side=tk.RIGHT, padx=(10, 0))
            
            # 창 위치 조정
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
            
            # 중앙 배치
            self.dialog.update_idletasks()
            x = (self.dialog.winfo_screenwidth() - dialog_width) // 2
            y = (self.dialog.winfo_screenheight() - dialog_height) // 2
            self.dialog.geometry(f"+{x}+{y}")
            
        except Exception as e:
            logger.error(f"업데이트 다이얼로그 생성 오류: {e}")
    
    def later(self):
        """나중에 업데이트"""
        self.result = 'later'
        self.dialog.destroy()
    
    def open_github(self):
        """GitHub 릴리즈 페이지 열기"""
        try:
            release_url = self.update_info.get('release_url', 
                                             f"https://github.com/{self.update_checker.repo_owner}/{self.update_checker.repo_name}/releases")
            webbrowser.open(release_url)
            logger.info(f"GitHub 페이지 열기: {release_url}")
        except Exception as e:
            logger.error(f"GitHub 페이지 열기 실패: {e}")
    
    def download_update(self):
        """업데이트 다운로드"""
        try:
            assets = self.update_info.get('download_assets', [])
            if not assets:
                messagebox.showwarning('다운로드 오류', '다운로드 가능한 파일이 없습니다.')
                return
            
            # 첫 번째 자산 선택 (또는 사용자가 선택하도록 할 수 있음)
            asset = assets[0]
            
            # 저장 위치 선택 (exe 파일 우선)
            if asset['name'].lower().endswith('.exe'):
                filetypes = [('실행 파일', '*.exe'), ('압축 파일', '*.zip'), ('모든 파일', '*.*')]
                defaultextension = '.exe'
            else:
                filetypes = [('압축 파일', '*.zip'), ('실행 파일', '*.exe'), ('모든 파일', '*.*')]
                defaultextension = '.zip'
            
            save_path = filedialog.asksaveasfilename(
                defaultextension=defaultextension,
                filetypes=filetypes,
                initialfile=asset['name']
            )
            
            if not save_path:
                return
            
            # 다운로드 진행
            progress = AdvancedProgressDialog(self.dialog, "업데이트 다운로드", 
                                            f"{asset['name']} 다운로드 중...", 
                                            cancelable=True)
            
            def download_worker():
                def progress_callback(percent):
                    progress.update(percent, f"다운로드 중... {percent:.1f}%")
                
                success = self.update_checker.download_update(
                    asset['download_url'], save_path, progress_callback)
                
                return {'success': success, 'file_path': save_path}
            
            def on_complete(result):
                progress.close()
                if result.get('success'):
                    messagebox.showinfo('다운로드 완료', 
                                      f'업데이트 파일이 다운로드되었습니다.\n\n파일 위치: {result["file_path"]}')
                    self.result = 'downloaded'
                    self.dialog.destroy()
                else:
                    messagebox.showerror('다운로드 실패', '업데이트 다운로드에 실패했습니다.')
            
            # 비동기 다운로드 실행 (이 부분은 메인 클래스의 task_manager를 사용해야 함)
            # 여기서는 간단히 동기 방식으로 처리
            try:
                def progress_callback(percent):
                    progress.update(percent, f"다운로드 중... {percent:.1f}%")
                
                success = self.update_checker.download_update(
                    asset['download_url'], save_path, progress_callback)
                
                progress.close()
                if success:
                    # exe 파일인 경우 실행 옵션 제공
                    if save_path.lower().endswith('.exe'):
                        result = messagebox.askyesnocancel(
                            '다운로드 완료', 
                            f'exe 파일 다운로드가 완료되었습니다!\n\n파일 위치: {save_path}\n\n지금 실행하시겠습니까?\n\n'
                            f'• 예: 새 버전 실행 (현재 프로그램 종료)\n'
                            f'• 아니오: 나중에 수동 실행\n'
                            f'• 취소: 파일 위치만 확인'
                        )
                        
                        if result is True:  # 예 - 지금 실행
                            try:
                                import subprocess
                                logger.info(f"새 버전 실행: {save_path}")
                                subprocess.Popen([save_path])
                                
                                # 현재 프로그램 종료 예약
                                self.parent.after(1000, lambda: self.parent.quit())
                                messagebox.showinfo('프로그램 전환', 
                                                  '새 버전이 실행됩니다.\n현재 프로그램은 곧 종료됩니다.')
                            except Exception as e:
                                logger.error(f"새 버전 실행 실패: {e}")
                                messagebox.showerror('실행 오류', 
                                                   f'새 버전 실행에 실패했습니다.\n수동으로 실행해주세요.\n\n파일: {save_path}')
                        
                        elif result is False:  # 아니오 - 나중에 실행
                            messagebox.showinfo('다운로드 완료', 
                                              f'exe 파일이 다운로드되었습니다.\n나중에 수동으로 실행해주세요.\n\n파일 위치: {save_path}')
                        
                        else:  # 취소 - 파일 위치만 확인
                            messagebox.showinfo('파일 위치', f'다운로드된 파일 위치:\n{save_path}')
                    
                    else:
                        # exe가 아닌 파일의 경우 기존 방식
                        messagebox.showinfo('다운로드 완료', 
                                          f'업데이트 파일이 다운로드되었습니다.\n\n파일 위치: {save_path}')
                    
                    self.result = 'downloaded'
                    self.dialog.destroy()
                else:
                    messagebox.showerror('다운로드 실패', 'exe 파일 다운로드에 실패했습니다.')
            except Exception as e:
                progress.close()
                logger.error(f"다운로드 오류: {e}")
                messagebox.showerror('다운로드 오류', f'다운로드 중 오류가 발생했습니다: {str(e)}')
                
        except Exception as e:
            logger.error(f"업데이트 다운로드 오류: {e}")
            messagebox.showerror('오류', f'다운로드 중 오류가 발생했습니다: {str(e)}')

class OptimizedFontManager:
    """최적화된 폰트 관리 클래스"""
    
    def __init__(self):
        self.korean_fonts = []
        self.korean_font_path = None
        self.ui_font = None
        self._font_cache = weakref.WeakValueDictionary()
        self._setup_fonts()
    
    def _setup_fonts(self):
        """시스템 폰트 설정"""
        try:
            font_candidates = [
                ('맑은 고딕', [
                    r'C:\Windows\Fonts\malgun.ttf',
                    r'C:\Windows\Fonts\malgunsl.ttf'
                ]),
                ('Malgun Gothic', [
                    r'C:\Windows\Fonts\malgun.ttf'
                ]),
                ('나눔고딕', [
                    r'C:\Windows\Fonts\NanumGothic.ttf',
                    r'C:\Windows\Fonts\나눔고딕.ttf'
                ]),
                ('Gulim', [r'C:\Windows\Fonts\gulim.ttc']),
                ('Dotum', [r'C:\Windows\Fonts\dotum.ttc']),
                ('Batang', [r'C:\Windows\Fonts\batang.ttc'])
            ]
            
            if sys.platform == 'darwin':
                font_candidates.extend([
                    ('AppleGothic', ['/System/Library/Fonts/AppleGothic.ttf']),
                    ('Helvetica', ['/System/Library/Fonts/Helvetica.ttc'])
                ])
            
            elif sys.platform.startswith('linux'):
                font_candidates.extend([
                    ('Noto Sans CJK KR', [
                        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'
                    ]),
                    ('DejaVu Sans', ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
                ])
            
            selected_font = '맑은 고딕'
            for font_name, paths in font_candidates:
                for path in paths:
                    if os.path.exists(path):
                        selected_font = font_name
                        self.korean_font_path = path
                        logger.info(f"✓ 한글 폰트 발견: {font_name} ({path})")
                        break
                if self.korean_font_path:
                    break
            
            self.ui_font = (selected_font, 10)
            self.ui_font_bold = (selected_font, 10, 'bold')
            self.ui_font_small = (selected_font, 8)
            self.title_font = (selected_font, 12, 'bold')
            self.status_font = (selected_font, 10, 'bold')
            self.text_font = (selected_font, 10)
            # 텍스트 입력용 한글 최적화 설정
            self.text_input_font = (selected_font, 11)
            
            logger.info(f"✓ UI 폰트 설정 완료: {selected_font}")
            
        except Exception as e:
            logger.error(f"폰트 설정 오류: {e}")
            self._setup_fallback_fonts()
    
    def _setup_fallback_fonts(self):
        """기본 폰트 설정"""
        self.ui_font = ('Arial', 10)
        self.ui_font_bold = ('Arial', 10, 'bold')
        self.ui_font_small = ('Arial', 10)
        self.title_font = ('Arial', 12, 'bold')
        self.status_font = ('Arial', 10, 'bold')
        self.text_font = ('Arial', 10)
        self.text_input_font = ('Arial', 11)
    
    def get_pil_font(self, size=12):
        """PIL용 폰트 반환"""
        try:
            cache_key = f"{self.korean_font_path}_{size}"
            
            if cache_key in self._font_cache:
                return self._font_cache[cache_key]
            
            font = None
            if self.korean_font_path and os.path.exists(self.korean_font_path):
                font = ImageFont.truetype(self.korean_font_path, size)
            else:
                font = ImageFont.load_default()
            
            self._font_cache[cache_key] = font
            return font
            
        except Exception as e:
            logger.debug(f"PIL 폰트 로드 실패: {e}")
            return ImageFont.load_default()
    
    def register_pdf_font(self):
        """PDF용 한글 폰트 등록"""
        font_name = 'Helvetica'
        try:
            if self.korean_font_path and os.path.exists(self.korean_font_path):
                pdfmetrics.registerFont(TTFont('Korean', self.korean_font_path))
                font_name = 'Korean'
                logger.info("✓ PDF 한글 폰트 등록 성공")
        except Exception as e:
            logger.warning(f"PDF 한글 폰트 등록 실패: {e}")
        
        return font_name

class AsyncTaskManager:
    """비동기 작업 관리자"""
    
    def __init__(self, root):
        self.root = root
        self.task_queue = queue.Queue()
        self.is_running = True
        self._start_worker()
    
    def _start_worker(self):
        """작업자 스레드 시작"""
        def worker():
            while self.is_running:
                try:
                    task = self.task_queue.get(timeout=1)
                    if task:
                        result = task['func'](*task['args'], **task['kwargs'])
                        if task['callback']:
                            self.root.after(0, lambda: task['callback'](result))
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"비동기 작업 오류: {e}")
                    if task.get('error_callback'):
                        self.root.after(0, lambda: task['error_callback'](e))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def submit_task(self, func, args=(), kwargs={}, callback=None, error_callback=None):
        """작업 제출"""
        task = {
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'callback': callback,
            'error_callback': error_callback
        }
        self.task_queue.put(task)
    
    def shutdown(self):
        """작업 관리자 종료"""
        self.is_running = False

"""
🎯 악어스튜디오 캡쳐 피드백 도구 V1.9.3 - 배포 최적화 버전
==================================================
- 영역 선택으로 다중 주석 선택/이동/삭제
- PDF 텍스트 주석 완벽 출력 (배경/테두리 제거)
- 빈 캔버스 생성 기능 추가
- UI 레이아웃 최적화
- PDF 정보 입력창 분리
- 모든 기능 디버그 및 최적화 완료

🚀 V1.9.3 배포 최적화:
- 동적 디버그 모드 (--debug 플래그 또는 DEBUG_MODE 환경변수)
- 프로덕션 로그 레벨 최적화 (WARNING 이상만 출력)
- 콘솔 창 자동 숨김 (프로덕션 모드)
- 디버그 출력 완전 제거 (프로덕션 모드)
==================================================
"""

import sys
import os
import threading
import time
import json
import io
import base64
import math
import logging
import traceback
import gc
import tempfile
import platform
import shutil
import weakref
from datetime import datetime
from pathlib import Path
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
# 🔥 [중복 제거됨] 첫 번째 V1.6.1 블록 - 모든 정의는 constants.py와 utils.py로 이동됨

# 🔥 [중복 제거됨] 두 번째 V1.6.1 블록 - 상단의 첫 번째 블록으로 통합됨

class SafeThreadExecutor:
    """Thread-safe 작업 실행기"""
    
    def __init__(self, max_workers=2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures = set()
        self._cleanup_completed()
    
    def submit(self, fn, *args, **kwargs):
        """작업 제출"""
        future = self.executor.submit(fn, *args, **kwargs)
        self.futures.add(future)
        return future
    
    def _cleanup_completed(self):
        """완료된 작업 정리"""
        completed = {f for f in self.futures if f.done()}
        self.futures -= completed
    
    def shutdown(self):
        """실행기 종료"""
        self.executor.shutdown(wait=False)

class SystemMonitor:
    """시스템 리소스 모니터링"""
    
    def __init__(self):
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None
        self.memory_warnings = 0
        # 🔥 웹툰 지원: 메모리 제한 대폭 증가 (1GB → 3GB)
        self.max_memory_mb = 3072  # 웹툰과 같은 큰 이미지들을 위해 3GB로 증가
        self._last_memory_check = 0
        self._memory_check_interval = 3  # 체크 간격 단축 (5초 → 3초)
    
    def get_memory_usage(self):
        """현재 메모리 사용량 반환 (MB)"""
        try:
            if self.process:
                current_time = time.time()
                if current_time - self._last_memory_check > self._memory_check_interval:
                    self._last_memory_check = current_time
                    return self.process.memory_info().rss / 1024 / 1024
                return getattr(self, '_cached_memory', 0)
            return 0
        except Exception:
            return 0
    
    def check_memory_limit(self):
        """메모리 제한 확인"""
        current_memory = self.get_memory_usage()
        self._cached_memory = current_memory
        
        if current_memory > self.max_memory_mb:
            self.memory_warnings += 1
            logger.warning(f"메모리 사용량 초과: {current_memory:.1f}MB")
            if self.memory_warnings > 3:
                return False
        return True
    
    def get_disk_space(self, path):
        """디스크 공간 확인 (MB)"""
        try:
            if PSUTIL_AVAILABLE:
                usage = psutil.disk_usage(path)
                return usage.free / 1024 / 1024
            return float('inf')
        except Exception:
            return float('inf')

class AdvancedProgressDialog:
    """향상된 진행 상황 표시 다이얼로그"""
    
    def __init__(self, parent, title, message, auto_close_ms=None, cancelable=False):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("450x180")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.canceled = False
        self.cancel_callback = None
        
        if auto_close_ms:
            self.dialog.after(auto_close_ms, self.close)

        # 창 중앙 배치
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 225
        y = (self.dialog.winfo_screenheight() // 2) - 90
        self.dialog.geometry(f"+{x}+{y}")
        
        # UI 구성
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.message_label = tk.Label(main_frame, text=message, 
                                     font=('맑은 고딕', 11, 'bold'))
        self.message_label.pack(pady=(0, 15))
        
        # 진행률 바와 퍼센트 표시를 함께
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate', length=350)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.percent_label = tk.Label(progress_frame, text="0%", font=('맑은 고딕', 9, 'bold'), width=5)
        self.percent_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.detail_label = tk.Label(main_frame, text="", 
                                    font=('맑은 고딕', 9), fg='#666')
        self.detail_label.pack()
        
        # 취소 버튼 (옵션)
        if cancelable:
            self.cancel_btn = tk.Button(main_frame, text="취소", 
                                       command=self.cancel,
                                       bg='#dc3545', fg='white',
                                       font=('맑은 고딕', 9))
            self.cancel_btn.pack(pady=(10, 0))
        
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel if cancelable else lambda: None)
        self.dialog.update()
    
    def update(self, value, detail=""):
        """진행률 업데이트"""
        try:
            if self.canceled:
                return False
                
            self.progress['value'] = min(100, max(0, value))
            self.percent_label.config(text=f"{int(value)}%")
            
            if detail:
                self.detail_label.config(text=detail)
            self.dialog.update()
            return True
        except Exception:
            return False
    
    def cancel(self):
        """취소 처리"""
        self.canceled = True
        if self.cancel_callback:
            self.cancel_callback()
        self.close()
    
    def set_cancel_callback(self, callback):
        """취소 콜백 설정"""
        self.cancel_callback = callback
    
    def close(self):
        """다이얼로그 닫기"""
        try:
            self.dialog.destroy()
        except Exception:
            pass

class SmartUndoManager:
    """스마트 되돌리기 관리 클래스"""
    
    def __init__(self, max_history=8):
        self.max_history = max_history
        self.histories = {}
        self._last_cleanup = time.time()
    
    def save_state(self, item_id, annotations):
        """현재 주석 상태 저장"""
        try:
            if item_id not in self.histories:
                self.histories[item_id] = deque(maxlen=self.max_history)
            
            state = [ann.copy() for ann in annotations]
            self.histories[item_id].append(state)
            
            if time.time() - self._last_cleanup > 300:
                self._cleanup_old_histories()
                
            logger.debug(f"상태 저장됨 - Item {item_id}: {len(state)}개 주석")
            
        except Exception as e:
            logger.error(f"상태 저장 오류: {e}")
    
    def undo(self, item_id):
        """되돌리기 실행"""
        try:
            if item_id not in self.histories or len(self.histories[item_id]) <= 1:
                return None
            
            self.histories[item_id].pop()
            if self.histories[item_id]:
                prev_state = self.histories[item_id][-1]
                restored_state = [ann.copy() for ann in prev_state]
                
                logger.debug(f"되돌리기 실행 - Item {item_id}: {len(restored_state)}개 주석")
                return restored_state
            
            return []
            
        except Exception as e:
            logger.error(f"되돌리기 오류: {e}")
            return None
    
    def can_undo(self, item_id):
        """되돌리기 가능한지 확인"""
        return (item_id in self.histories and len(self.histories[item_id]) > 1)
    
    def _cleanup_old_histories(self):
        """오래된 히스토리 정리"""
        try:
            empty_keys = [k for k, v in self.histories.items() if not v]
            for k in empty_keys:
                del self.histories[k]
            
            self._last_cleanup = time.time()
            
        except Exception as e:
            logger.debug(f"히스토리 정리 오류: {e}")
    
    def clear_history(self, item_id):
        """특정 항목의 히스토리 초기화"""
        if item_id in self.histories:
            self.histories[item_id].clear()
    
    def clear_all(self):
        """모든 히스토리 초기화"""
        self.histories.clear()

class OptimizedFontManager:
    """최적화된 폰트 관리 클래스"""
    
    def __init__(self):
        self.korean_fonts = []
        self.korean_font_path = None
        self.ui_font = None
        self._font_cache = weakref.WeakValueDictionary()
        self._setup_fonts()
    
    def _setup_fonts(self):
        """시스템 폰트 설정"""
        try:
            font_candidates = [
                ('맑은 고딕', [
                    r'C:\Windows\Fonts\malgun.ttf',
                    r'C:\Windows\Fonts\malgunsl.ttf'
                ]),
                ('Malgun Gothic', [
                    r'C:\Windows\Fonts\malgun.ttf'
                ]),
                ('나눔고딕', [
                    r'C:\Windows\Fonts\NanumGothic.ttf',
                    r'C:\Windows\Fonts\나눔고딕.ttf'
                ]),
                ('Gulim', [r'C:\Windows\Fonts\gulim.ttc']),
                ('Dotum', [r'C:\Windows\Fonts\dotum.ttc']),
                ('Batang', [r'C:\Windows\Fonts\batang.ttc'])
            ]
            
            if sys.platform == 'darwin':
                font_candidates.extend([
                    ('AppleGothic', ['/System/Library/Fonts/AppleGothic.ttf']),
                    ('Helvetica', ['/System/Library/Fonts/Helvetica.ttc'])
                ])
            
            elif sys.platform.startswith('linux'):
                font_candidates.extend([
                    ('Noto Sans CJK KR', [
                        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'
                    ]),
                    ('DejaVu Sans', ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
                ])
            
            selected_font = '맑은 고딕'
            for font_name, paths in font_candidates:
                for path in paths:
                    if os.path.exists(path):
                        selected_font = font_name
                        self.korean_font_path = path
                        logger.info(f"✓ 한글 폰트 발견: {font_name} ({path})")
                        break
                if self.korean_font_path:
                    break
            
            self.ui_font = (selected_font, 10)
            self.ui_font_bold = (selected_font, 10, 'bold')
            self.ui_font_small = (selected_font, 9)
            self.title_font = (selected_font, 12, 'bold')
            self.status_font = (selected_font, 10, 'bold')
            self.text_font = (selected_font, 10)
            # 텍스트 입력용 한글 최적화 설정
            self.text_input_font = (selected_font, 11)
            
            logger.info(f"✓ UI 폰트 설정 완료: {selected_font}")
            
        except Exception as e:
            logger.error(f"폰트 설정 오류: {e}")
            self._setup_fallback_fonts()
    
    def _setup_fallback_fonts(self):
        """기본 폰트 설정"""
        self.ui_font = ('Arial', 10)
        self.ui_font_bold = ('Arial', 10, 'bold')
        self.ui_font_small = ('Arial', 9)
        self.title_font = ('Arial', 12, 'bold')
        self.status_font = ('Arial', 10, 'bold')
        self.text_font = ('Arial', 10)
        self.text_input_font = ('Arial', 11)
    
    def get_pil_font(self, size=12):
        """PIL용 폰트 반환"""
        try:
            cache_key = f"{self.korean_font_path}_{size}"
            
            if cache_key in self._font_cache:
                return self._font_cache[cache_key]
            
            font = None
            if self.korean_font_path and os.path.exists(self.korean_font_path):
                font = ImageFont.truetype(self.korean_font_path, size)
            else:
                font = ImageFont.load_default()
            
            self._font_cache[cache_key] = font
            return font
            
        except Exception as e:
            logger.debug(f"PIL 폰트 로드 실패: {e}")
            return ImageFont.load_default()
    
    def register_pdf_font(self):
        """PDF용 한글 폰트 등록"""
        font_name = 'Helvetica'
        try:
            if self.korean_font_path and os.path.exists(self.korean_font_path):
                pdfmetrics.registerFont(TTFont('Korean', self.korean_font_path))
                font_name = 'Korean'
                logger.info("✓ PDF 한글 폰트 등록 성공")
        except Exception as e:
            logger.warning(f"PDF 한글 폰트 등록 실패: {e}")
        
        return font_name

class AsyncTaskManager:
    """비동기 작업 관리자"""
    
    def __init__(self, root):
        self.root = root
        self.task_queue = queue.Queue()
        self.is_running = True
        self._start_worker()
    
    def _start_worker(self):
        """작업자 스레드 시작"""
        def worker():
            while self.is_running:
                try:
                    task = self.task_queue.get(timeout=1)
                    if task:
                        result = task['func'](*task['args'], **task['kwargs'])
                        if task['callback']:
                            self.root.after(0, lambda: task['callback'](result))
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"비동기 작업 오류: {e}")
                    if task.get('error_callback'):
                        self.root.after(0, lambda: task['error_callback'](e))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def submit_task(self, func, args=(), kwargs={}, callback=None, error_callback=None):
        """작업 제출"""
        task = {
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'callback': callback,
            'error_callback': error_callback
        }
        self.task_queue.put(task)
    
    def shutdown(self):
        """작업 관리자 종료"""
        self.is_running = False

class HighQualityPDFGenerator:
    """고화질 PDF 생성기"""
    
    def __init__(self, font_manager, app_instance=None):
        self.font_manager = font_manager
        self.app = app_instance
        self.target_dpi = 300
        self.vector_annotations = True
        self.dragging_text = None
        self.drag_start_x = None
        self.drag_start_y = None
        self.original_text_x = None
        self.original_text_y = None
        # PDF 가독성 모드 옵션 (다이얼로그에서 전달받음)
        self.pdf_readability_mode = False  # 기본값은 항상 False, 명시적으로 설정해야만 True
        
    def set_readability_mode(self, enabled):
        """PDF 가독성 모드 설정"""
        self.pdf_readability_mode = enabled
        
    def create_high_quality_combined_image(self, item, target_width=None, target_height=None):
        """최고 화질의 합성 이미지 생성 (투명도 완벽 지원)"""
        try:
            original_image = item['image'].copy()
            annotations = item.get('annotations', [])
            logger.debug(f"합성 이미지 생성 시작: 기본 크기 {original_image.width}x{original_image.height}, 주석 {len(annotations)}개")
            
            if target_width and target_height:
                original_ratio = original_image.width / original_image.height
                target_ratio = target_width / target_height
                
                if original_ratio > target_ratio:
                    new_width = target_width
                    new_height = int(target_width / original_ratio)
                else:
                    new_height = target_height
                    new_width = int(target_height * original_ratio)
                
                if new_width != original_image.width or new_height != original_image.height:
                    logger.debug(f"이미지 크기 조정: {original_image.width}x{original_image.height} -> {new_width}x{new_height}")
                    original_image = original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 🔥 투명도가 있는 이미지 주석 확인
            image_annotations = [ann for ann in annotations if ann.get('type') == 'image']
            has_transparent_images = any(
                ann.get('opacity', 100) < 100 
                for ann in image_annotations
            )
            
            logger.info(f"🎨 이미지 주석 분석: 총 {len(image_annotations)}개, 투명도 있음: {has_transparent_images}")
            
            if has_transparent_images:
                # 🔥 투명도가 있는 경우 RGBA 모드 유지
                logger.info("🎨 투명도 감지: RGBA 모드로 처리")
                
                if original_image.mode != 'RGBA':
                    original_image = original_image.convert('RGBA')
                
                # RGBA 모드에서 투명도 지원하는 주석 그리기
                draw = ImageDraw.Draw(original_image)
                
                for i, annotation in enumerate(annotations):
                    try:
                        if annotation.get('type') == 'image':
                            # 투명도 지원 이미지 주석 그리기
                            self._draw_transparent_image_annotation(original_image, annotation)
                            logger.debug(f"투명도 이미지 주석 {i+1} 완료")
                        else:
                            # 다른 주석들은 기존 방식
                            self._draw_high_quality_annotation(draw, annotation, original_image.size)
                    except Exception as e:
                        logger.error(f"주석 {i+1} 그리기 오류: {e}")
                        continue
                
                logger.info(f"🎨 투명도 지원 합성 완료: {original_image.mode}, 크기: {original_image.width}x{original_image.height}")
                return original_image
            
            else:
                # 🔥 투명도가 없는 경우만 RGB 변환
                logger.info("🎨 투명도 없음: RGB 모드로 처리")
                
                if original_image.mode != 'RGB':
                    rgb_image = Image.new('RGB', original_image.size, (255, 255, 255))
                    if 'A' in original_image.mode:
                        rgb_image.paste(original_image, mask=original_image.split()[-1])
                    else:
                        rgb_image.paste(original_image)
                    original_image = rgb_image
                    logger.debug(f"RGB 변환 완료: {original_image.mode}")
                
                draw = ImageDraw.Draw(original_image)
                
                # 주석 그리기
                for i, annotation in enumerate(annotations):
                    try:
                        self._draw_high_quality_annotation(draw, annotation, original_image.size)
                    except Exception as e:
                        logger.error(f"주석 {i+1} 그리기 오류: {e}")
                        continue
                
                logger.debug(f"최종 합성 이미지: {original_image.width}x{original_image.height}, 모드: {original_image.mode}")
                return original_image
                
        except Exception as e:
            logger.error(f"고화질 이미지 생성 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return item['image']
    
    def _draw_high_quality_annotation(self, draw, annotation, image_size):
        """고화질 주석 그리기"""
        try:
            ann_type = annotation['type']
            color = annotation.get('color', '#ff0000')
            # 🔥 고화질 이미지에서 선 두께 조정 - 원본에 더 가깝게
            base_width = annotation.get('width', 2)
            width = max(2, int(base_width * 1.3))  # 기존 2배에서 1.3배로 조정
            
            if ann_type == 'arrow':
                x1, y1 = annotation['start_x'], annotation['start_y']
                x2, y2 = annotation['end_x'], annotation['end_y']
                

                
                # 🔥 PDF용 개선된 화살표 그리기
                if abs(x2 - x1) > 1 or abs(y2 - y1) > 1:
                    angle = math.atan2(y2 - y1, x2 - x1)
                    
                    # 동적 화살표 크기 계산
                    arrow_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                    base_arrow_size = max(20, width * 3)
                    max_arrow_size = arrow_length * 0.3
                    arrow_size = min(base_arrow_size, max_arrow_size)
                    arrow_size = max(arrow_size, 15)  # PDF에서는 최소 크기를 조금 더 크게
                    
                    # 작은 화살표는 더 날카롭게
                    angle_offset = math.pi / 8 if arrow_size < 30 else math.pi / 6
                    
                    # 삼각형이 라인보다 앞으로 돌출되도록 계산
                    base_distance = arrow_size * 0.7
                    base_x = x2 - base_distance * math.cos(angle)
                    base_y = y2 - base_distance * math.sin(angle)
                    
                    # 가독성 모드: 흰색 아웃라인 먼저 그리기
                    if self.pdf_readability_mode:
                        # 흰색 아웃라인 라인
                        draw.line([(x1, y1), (base_x, base_y)], fill='white', width=width+2)
                        
                        # 삼각형 끝점을 더 앞으로 돌출시키기
                        extend_distance = arrow_size * 0.15
                        tip_x = x2 + extend_distance * math.cos(angle)
                        tip_y = y2 + extend_distance * math.sin(angle)
                        
                        # 화살표 날개 좌표 계산
                        wing1_x = x2 - arrow_size * math.cos(angle - angle_offset)
                        wing1_y = y2 - arrow_size * math.sin(angle - angle_offset)
                        wing2_x = x2 - arrow_size * math.cos(angle + angle_offset)
                        wing2_y = y2 - arrow_size * math.sin(angle + angle_offset)
                        
                        # 흰색 아웃라인 삼각형
                        arrow_points = [(tip_x, tip_y), (wing1_x, wing1_y), (wing2_x, wing2_y)]
                        draw.polygon(arrow_points, fill='white', outline='white')
                    
                    # 화살표 라인을 삼각형 기저부까지만 그리기
                    draw.line([(x1, y1), (base_x, base_y)], fill=color, width=width)
                    
                    # 삼각형 끝점을 더 앞으로 돌출시키기
                    extend_distance = arrow_size * 0.15
                    tip_x = x2 + extend_distance * math.cos(angle)
                    tip_y = y2 + extend_distance * math.sin(angle)
                    
                    # 화살표 날개 좌표 계산
                    wing1_x = x2 - arrow_size * math.cos(angle - angle_offset)
                    wing1_y = y2 - arrow_size * math.sin(angle - angle_offset)
                    wing2_x = x2 - arrow_size * math.cos(angle + angle_offset)
                    wing2_y = y2 - arrow_size * math.sin(angle + angle_offset)
                    
                    # 뾰족하고 돌출된 삼각형 그리기
                    arrow_points = [(tip_x, tip_y), (wing1_x, wing1_y), (wing2_x, wing2_y)]
                    draw.polygon(arrow_points, fill=color, outline=color)
                else:
                    # 화살표가 너무 작은 경우 단순 라인
                    if self.pdf_readability_mode:
                        draw.line([(x1, y1), (x2, y2)], fill='white', width=width+2)
                    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
            
            elif ann_type == 'line':
                # 라인 그리기 (화살표 머리 없는 단순한 선)
                x1, y1 = annotation['start_x'], annotation['start_y']
                x2, y2 = annotation['end_x'], annotation['end_y']
                
                # 가독성 모드: 흰색 아웃라인
                if self.pdf_readability_mode:
                    draw.line([(x1, y1), (x2, y2)], fill='white', width=width+2)
                
                draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
            
            elif ann_type == 'pen':
                points = annotation.get('points', [])
                if len(points) > 1:
                    smoothed_points = self._smooth_path(points)
                    
                    # 가독성 모드: 흰색 아웃라인
                    if self.pdf_readability_mode:
                        for i in range(len(smoothed_points) - 1):
                            draw.line([smoothed_points[i], smoothed_points[i+1]], 
                                    fill='white', width=width+2)
                    
                    # 원래 색상으로 그리기
                    for i in range(len(smoothed_points) - 1):
                        draw.line([smoothed_points[i], smoothed_points[i+1]], 
                                fill=color, width=width)
            
            elif ann_type == 'oval':
                x1, y1 = annotation['x1'], annotation['y1']
                x2, y2 = annotation['x2'], annotation['y2']
                
                # 가독성 모드: 흰색 아웃라인
                if self.pdf_readability_mode:
                    draw.ellipse([min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)], 
                               outline='white', width=width+2)
                
                draw.ellipse([min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)], 
                           outline=color, width=width)
            
            elif ann_type == 'rect':
                x1, y1 = annotation['x1'], annotation['y1']
                x2, y2 = annotation['x2'], annotation['y2']
                
                # 가독성 모드: 흰색 아웃라인
                if self.pdf_readability_mode:
                    draw.rectangle([min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)], 
                                 outline='white', width=width+2)
                
                draw.rectangle([min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)], 
                             outline=color, width=width)
            
            elif ann_type == 'text':
                x, y = annotation['x'], annotation['y']
                text = annotation.get('text', '')
                base_font_size = annotation.get('font_size', 12)
                
                # 🔥 원본 크기와 동일하게 폰트 크기 유지 (2배 과대화 제거)
                font_size = max(base_font_size, 10)  # 최소 10px 보장
                font = self.font_manager.get_pil_font(font_size)
                
                # 가독성 모드: 텍스트 배경 추가 (글자 크기에 비례한 적절한 여백)
                if self.pdf_readability_mode and text.strip():
                    # 텍스트 크기 측정
                    bbox = draw.textbbox((x, y), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    
                    # 폰트 크기에 비례한 적절한 여백 (폰트 크기의 약 15%)
                    padding = max(3, font_size * 0.15)
                    bg_x1 = x - padding
                    bg_y1 = y - padding
                    bg_x2 = x + text_width + padding
                    bg_y2 = y + text_height + padding
                    
                    # 흰색 배경 그리기 (불투명하게)
                    draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], 
                                 fill='white', outline='#d0d0d0')
                
                # 텍스트 그리기
                draw.text((x, y), text, fill=color, font=font)
            
            elif ann_type == 'image':
                # 🔥 중요: 이미지 주석은 여기서 처리하지 않음!
                # _draw_transparent_image_annotation 메서드에서 별도 처리
                logger.debug("이미지 주석은 투명도 전용 메서드에서 처리됨")
                return
        
        except Exception as e:
            logger.debug(f"개별 주석 그리기 오류: {e}")
    
    def _smooth_path(self, points):
        """펜 경로 스무딩"""
        if len(points) <= 2:
            return points
        
        smoothed = [points[0]]
        
        for i in range(1, len(points) - 1):
            prev_point = points[i - 1]
            curr_point = points[i]
            next_point = points[i + 1]
            
            smooth_x = (prev_point[0] + curr_point[0] + next_point[0]) / 3
            smooth_y = (prev_point[1] + curr_point[1] + next_point[1]) / 3
            
            smoothed.append((smooth_x, smooth_y))
        
        smoothed.append(points[-1])
        return smoothed
    
    def create_vector_pdf_page(self, canvas, item, index, page_width, page_height):
        """벡터 기반 PDF 페이지 생성 - 하단 여백 축소"""
        try:
            margin = 50
            usable_width = page_width - (margin * 2)
            
            feedback_text = item.get('feedback_text', '').strip()
            text_area_height = 0
            bottom_margin = 25  # 🔥 하단 여백 대폭 축소 (기존 60 → 25)
            
            if feedback_text:
                korean_font = self.font_manager.register_pdf_font()
                temp_canvas = pdf_canvas.Canvas("temp.pdf", pagesize=A4)
                max_text_width = usable_width - 40
                text_lines = self._wrap_text_for_pdf(feedback_text, max_text_width, korean_font, 11, temp_canvas)
                
                line_height = 18
                title_space = 30  # 제목 공간 대폭 축소 (60 → 30)
                text_area_height = max(60, len(text_lines) * line_height + title_space + 20)  # 최소값 절반 축소 (120 → 60), 여백 절반 축소 (40 → 20)
                
                max_text_height = page_height * 0.4
                if text_area_height > max_text_height:
                    text_area_height = max_text_height
            
            image_text_gap = 25
            usable_height = page_height - (margin * 2) - bottom_margin - text_area_height - image_text_gap
            
            img = item['image']
            img_ratio = img.width / img.height
            
            if img.width > usable_width or img.height > usable_height:
                if img_ratio > (usable_width / usable_height):
                    new_width = usable_width
                    new_height = usable_width / img_ratio
                else:
                    new_height = usable_height
                    new_width = usable_height * img_ratio
            else:
                new_width = img.width
                new_height = img.height
            
            img_x = (page_width - new_width) / 2
            img_y = page_height - margin - new_height - 10
            
            clean_image = self.create_clean_image_for_pdf(item)
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                high_res_width = int(new_width * 2)
                high_res_height = int(new_height * 2)
                
                if high_res_width != clean_image.width or high_res_height != clean_image.height:
                    clean_image = clean_image.resize((high_res_width, high_res_height), Image.Resampling.LANCZOS)
                
                clean_image.save(tmp_file.name, format='PNG', optimize=False, compress_level=0)
                
                canvas.drawImage(tmp_file.name, img_x, img_y, new_width, new_height, preserveAspectRatio=True)
                
                try:
                    os.unlink(tmp_file.name)
                except:
                    pass
            
            self.draw_vector_annotations_on_pdf(canvas, item, img_x, img_y, new_width, new_height)
            
            if feedback_text:
                text_start_y = img_y - image_text_gap
                self._add_feedback_text_to_pdf(canvas, item, index, text_start_y, text_area_height, page_width, margin)
            
            # 꼬리말 추가 (첫 장만 출력 옵션 지원)
            if self.app and hasattr(self.app, 'project_footer') and self.app.project_footer.get():
                # 첫 장만 출력 설정 확인
                show_footer = True
                if hasattr(self.app, 'footer_first_page_only') and self.app.footer_first_page_only.get():
                    # 🔥 제목 페이지가 있을 때는 피드백 페이지에서 꼬리말 출력하지 않음
                    skip_title = getattr(self.app, 'skip_title_page', False)
                    if skip_title:
                        show_footer = (index == 0)  # 제목 페이지가 없으면 첫 번째 피드백 페이지에만 표시
                    else:
                        show_footer = False  # 제목 페이지가 있으면 피드백 페이지에서는 꼬리말 출력하지 않음
                
                if show_footer:
                    korean_font = self.font_manager.register_pdf_font()
                    canvas.setFont(korean_font, 10)
                    footer_text = self.app.project_footer.get().strip()
                    footer_width = canvas.stringWidth(footer_text, korean_font, 10)
                    canvas.drawString((page_width - footer_width) / 2, 15, footer_text)  # 꼬리말 더 아래로 (25 → 15)
            
            # 🔥 페이지 번호 계산 (첫장 제외 시 조정)
            skip_title = getattr(self.app, 'skip_title_page', False)
            page_number = index + 1 if skip_title else index + 2
            
            canvas.setFont('Helvetica', 10)
            canvas.drawString(page_width - 80, 15, f"- {page_number} -")  # 페이지 번호 더 아래로 (25 → 15)
            
        except Exception as e:
            logger.error(f"벡터 PDF 페이지 생성 오류: {e}")
            self._fallback_pdf_page(canvas, item, index, page_width, page_height)

    def create_clean_image_for_pdf(self, item):
        """PDF용 깨끗한 이미지 생성 (주석 제외)"""
        try:
            clean_image = item['image'].copy()
            
            if clean_image.mode != 'RGB':
                rgb_image = Image.new('RGB', clean_image.size, (255, 255, 255))
                if 'A' in clean_image.mode:
                    rgb_image.paste(clean_image, mask=clean_image.split()[-1])
                else:
                    rgb_image.paste(clean_image)
                clean_image = rgb_image
            
            return clean_image
            
        except Exception as e:
            logger.error(f"깨끗한 이미지 생성 오류: {e}")
            return item['image']

    def draw_vector_annotations_on_pdf(self, canvas, item, img_x, img_y, img_width, img_height):
        """PDF에 벡터 기반 주석 그리기 (개선된 텍스트 처리)"""
        try:
            if not item.get('annotations'):
                return
            
            scale_x = img_width / item['image'].width
            scale_y = img_height / item['image'].height
            
            for annotation in item['annotations']:
                try:
                    ann_type = annotation['type']
                    color_hex = annotation.get('color', '#ff0000')
                    
                    if color_hex.startswith('#'):
                        color_hex = color_hex[1:]
                    r = int(color_hex[0:2], 16) / 255.0
                    g = int(color_hex[2:4], 16) / 255.0
                    b = int(color_hex[4:6], 16) / 255.0
                    
                    canvas.setStrokeColorRGB(r, g, b)
                    canvas.setFillColorRGB(r, g, b)
                    
                    # 🔥 선 두께 스케일링 조정 - 원본에 더 가깝게
                    base_width = annotation.get('width', 2)
                    # 스케일 팩터를 줄여서 원본 크기에 더 가깝게 유지
                    scale_factor = min(scale_x, scale_y) * 0.7  # 기존 스케일의 70%로 조정
                    line_width = max(1.0, base_width * scale_factor)  # 최소 두께 증가
                    canvas.setLineWidth(line_width)
                    
                    if ann_type == 'arrow':
                        x1 = img_x + annotation['start_x'] * scale_x
                        y1 = img_y + (item['image'].height - annotation['start_y']) * scale_y
                        x2 = img_x + annotation['end_x'] * scale_x
                        y2 = img_y + (item['image'].height - annotation['end_y']) * scale_y
                        
                        # 가독성 모드: 흰색 아웃라인
                        if self.pdf_readability_mode:
                            canvas.setStrokeColorRGB(1, 1, 1)  # 흰색
                            canvas.setLineWidth(line_width + 2)
                        
                        # 🔥 PDF ReportLab용 개선된 화살표 그리기 (좌표계 수정)
                        if abs(x2 - x1) > 1 or abs(y2 - y1) > 1:
                            # PDF 좌표계에 맞는 올바른 각도 계산
                            angle = math.atan2(y2 - y1, x2 - x1)
                            
                            # 동적 화살표 크기 계산
                            arrow_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                            base_arrow_size = max(10, line_width * 3)
                            max_arrow_size = arrow_length * 0.3
                            arrow_size = min(base_arrow_size, max_arrow_size)
                            arrow_size = max(arrow_size, 8)  # PDF에서 최소 크기
                            
                            # 작은 화살표는 더 날카롭게
                            angle_offset = math.pi / 8 if arrow_size < 20 else math.pi / 6
                            
                            # 삼각형이 라인보다 앞으로 돌출되도록 계산
                            base_distance = arrow_size * 0.7
                            base_x = x2 - base_distance * math.cos(angle)
                            base_y = y2 - base_distance * math.sin(angle)
                            
                            # 화살표 라인을 삼각형 기저부까지만 그리기
                            canvas.line(x1, y1, base_x, base_y)
                            
                            # 삼각형 끝점을 더 앞으로 돌출시키기
                            extend_distance = arrow_size * 0.15
                            tip_x = x2 + extend_distance * math.cos(angle)
                            tip_y = y2 + extend_distance * math.sin(angle)
                            
                            # 화살표 날개 좌표 계산
                            wing1_x = x2 - arrow_size * math.cos(angle - angle_offset)
                            wing1_y = y2 - arrow_size * math.sin(angle - angle_offset)
                            wing2_x = x2 - arrow_size * math.cos(angle + angle_offset)
                            wing2_y = y2 - arrow_size * math.sin(angle + angle_offset)
                            
                            # 뾰족하고 돌출된 삼각형 그리기 (흰색 아웃라인)
                            if self.pdf_readability_mode:
                                path = canvas.beginPath()
                                path.moveTo(tip_x, tip_y)
                                path.lineTo(wing1_x, wing1_y)
                                path.lineTo(wing2_x, wing2_y)
                                path.close()
                                canvas.drawPath(path, fill=1, stroke=1)
                                canvas.line(x1, y1, base_x, base_y)
                                
                                # 원래 색상으로 다시 설정
                                canvas.setStrokeColorRGB(r, g, b)
                                canvas.setFillColorRGB(r, g, b)
                                canvas.setLineWidth(line_width)
                            
                            # 화살표 라인을 삼각형 기저부까지만 그리기
                            canvas.line(x1, y1, base_x, base_y)
                            
                            # 뾰족하고 돌출된 삼각형 그리기
                            path = canvas.beginPath()
                            path.moveTo(tip_x, tip_y)
                            path.lineTo(wing1_x, wing1_y)
                            path.lineTo(wing2_x, wing2_y)
                            path.close()
                            canvas.drawPath(path, fill=1, stroke=1)
                        else:
                            # 화살표가 너무 작은 경우 단순 라인
                            if self.pdf_readability_mode:
                                canvas.line(x1, y1, x2, y2)
                                # 원래 색상으로 다시 설정
                                canvas.setStrokeColorRGB(r, g, b)
                                canvas.setLineWidth(line_width)
                            canvas.line(x1, y1, x2, y2)
                    
                    elif ann_type == 'line':
                        # 라인 그리기 (화살표 머리 없는 단순한 선)
                        x1 = img_x + annotation['start_x'] * scale_x
                        y1 = img_y + (item['image'].height - annotation['start_y']) * scale_y
                        x2 = img_x + annotation['end_x'] * scale_x
                        y2 = img_y + (item['image'].height - annotation['end_y']) * scale_y
                        
                        # 가독성 모드: 흰색 아웃라인
                        if self.pdf_readability_mode:
                            canvas.setStrokeColorRGB(1, 1, 1)  # 흰색
                            canvas.setLineWidth(line_width + 2)
                            canvas.line(x1, y1, x2, y2)
                            # 원래 색상으로 다시 설정
                            canvas.setStrokeColorRGB(r, g, b)
                            canvas.setLineWidth(line_width)
                        
                        canvas.line(x1, y1, x2, y2)
                    
                    elif ann_type == 'pen':
                        points = annotation.get('points', [])
                        if len(points) > 1:
                            # 가독성 모드: 흰색 아웃라인
                            if self.pdf_readability_mode:
                                canvas.setStrokeColorRGB(1, 1, 1)  # 흰색
                                canvas.setLineWidth(line_width + 2)
                                for i in range(len(points) - 1):
                                    x1 = img_x + points[i][0] * scale_x
                                    y1 = img_y + (item['image'].height - points[i][1]) * scale_y
                                    x2 = img_x + points[i+1][0] * scale_x
                                    y2 = img_y + (item['image'].height - points[i+1][1]) * scale_y
                                    canvas.line(x1, y1, x2, y2)
                                # 원래 색상으로 다시 설정
                                canvas.setStrokeColorRGB(r, g, b)
                                canvas.setLineWidth(line_width)
                            
                            # 원래 색상으로 그리기
                            for i in range(len(points) - 1):
                                x1 = img_x + points[i][0] * scale_x
                                y1 = img_y + (item['image'].height - points[i][1]) * scale_y
                                x2 = img_x + points[i+1][0] * scale_x
                                y2 = img_y + (item['image'].height - points[i+1][1]) * scale_y
                                canvas.line(x1, y1, x2, y2)
                    
                    elif ann_type == 'oval':
                        x1 = img_x + annotation['x1'] * scale_x
                        y1 = img_y + (item['image'].height - annotation['y1']) * scale_y
                        x2 = img_x + annotation['x2'] * scale_x
                        y2 = img_y + (item['image'].height - annotation['y2']) * scale_y
                        
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2
                        width = abs(x2 - x1)
                        height = abs(y2 - y1)
                        
                        # 가독성 모드: 흰색 아웃라인
                        if self.pdf_readability_mode:
                            canvas.setStrokeColorRGB(1, 1, 1)  # 흰색
                            canvas.setLineWidth(line_width + 2)
                            canvas.ellipse(center_x - width/2, center_y - height/2,
                                         center_x + width/2, center_y + height/2,
                                         stroke=1, fill=0)
                            # 원래 색상으로 다시 설정
                            canvas.setStrokeColorRGB(r, g, b)
                            canvas.setLineWidth(line_width)
                        
                        canvas.ellipse(center_x - width/2, center_y - height/2,
                                     center_x + width/2, center_y + height/2,
                                     stroke=1, fill=0)
                    
                    elif ann_type == 'rect':
                        x1 = img_x + annotation['x1'] * scale_x
                        y1 = img_y + (item['image'].height - annotation['y1']) * scale_y
                        x2 = img_x + annotation['x2'] * scale_x
                        y2 = img_y + (item['image'].height - annotation['y2']) * scale_y
                        
                        # 가독성 모드: 흰색 아웃라인
                        if self.pdf_readability_mode:
                            canvas.setStrokeColorRGB(1, 1, 1)  # 흰색
                            canvas.setLineWidth(line_width + 2)
                            canvas.rect(min(x1, x2), min(y1, y2),
                                       abs(x2 - x1), abs(y2 - y1),
                                       stroke=1, fill=0)
                            # 원래 색상으로 다시 설정
                            canvas.setStrokeColorRGB(r, g, b)
                            canvas.setLineWidth(line_width)
                        
                        canvas.rect(min(x1, x2), min(y1, y2),
                                   abs(x2 - x1), abs(y2 - y1),
                                   stroke=1, fill=0)
                    
                    elif ann_type == 'text':
                        # 🔥 텍스트 주석 좌표와 크기 정확히 맞추기
                        x = img_x + annotation['x'] * scale_x
                        # PDF 좌표계에서 y축은 하단부터 시작하므로 올바른 계산
                        y = img_y + (item['image'].height - annotation['y']) * scale_y
                        text = annotation.get('text', '')
                        
                        # 🔥 원본과 완전히 동일한 폰트 크기 사용 (스케일링 완전 제거)
                        base_font_size = annotation.get('font_size', 12)
                        # PDF에서 원본과 동일한 크기 유지
                        pdf_font_size = max(10, base_font_size)  # 최소 10px 보장
                        
                        korean_font = self.font_manager.register_pdf_font()
                        canvas.setFont(korean_font, pdf_font_size)
                        
                        # 가독성 모드: 텍스트 배경 추가
                        if self.pdf_readability_mode and text.strip():
                            text_width = canvas.stringWidth(text, korean_font, pdf_font_size)
                            padding = max(3, pdf_font_size * 0.15)
                            
                            # 흰색 배경 사각형
                            canvas.setFillColorRGB(1, 1, 1)  # 흰색
                            canvas.setStrokeColorRGB(0.8, 0.8, 0.8)  # 회색 테두리
                            canvas.setLineWidth(0.5)
                            canvas.rect(x - padding, y - pdf_font_size - padding,
                                       text_width + padding * 2, pdf_font_size + padding * 2,
                                       stroke=1, fill=1)
                        
                        # 텍스트 그리기 - 위치 보정
                        canvas.setFillColorRGB(r, g, b)
                        canvas.drawString(x, y - pdf_font_size, text)
                    
                    elif ann_type == 'image':
                        try:
                            # 이미지 주석 좌표 계산 (PDF 좌표계 고려)
                            x = img_x + annotation['x'] * scale_x
                            y = img_y + (item['image'].height - annotation['y']) * scale_y
                            width = annotation['width'] * scale_x
                            height = annotation['height'] * scale_y
                            
                            # base64 이미지 디코딩
                            image_data = base64.b64decode(annotation['image_data'])
                            img = Image.open(io.BytesIO(image_data))
                            
                            # 🔥 고해상도 처리를 위한 DPI 스케일링 계산
                            # PDF는 300 DPI가 표준이므로 고품질을 위해 2-3배 크기로 처리
                            quality_multiplier = 2.5  # 품질 향상을 위한 배율
                            high_res_width = max(int(width * quality_multiplier), int(annotation['width'] * quality_multiplier))
                            high_res_height = max(int(height * quality_multiplier), int(annotation['height'] * quality_multiplier))
                            
                            # 원본 이미지가 작을 경우 최소 크기 보장
                            min_size = 200  # 최소 픽셀 크기
                            if high_res_width < min_size or high_res_height < min_size:
                                aspect_ratio = img.width / img.height
                                if high_res_width < min_size:
                                    high_res_width = min_size
                                    high_res_height = int(min_size / aspect_ratio)
                                if high_res_height < min_size:
                                    high_res_height = min_size
                                    high_res_width = int(min_size * aspect_ratio)
                            
                            # 변형 적용 (고해상도로 처리하기 전에)
                            if annotation.get('flip_horizontal', False):
                                img = img.transpose(Image.FLIP_LEFT_RIGHT)
                            if annotation.get('flip_vertical', False):
                                img = img.transpose(Image.FLIP_TOP_BOTTOM)
                            
                            rotation = annotation.get('rotation', 0)
                            if rotation != 0:
                                img = img.rotate(-rotation, expand=True)
                            
                            # 🔥 고품질 리샘플링으로 크기 조정
                            img = img.resize((int(high_res_width), int(high_res_height)), Image.Resampling.LANCZOS)
                            
                            # 투명도 처리
                            opacity = annotation.get('opacity', 100) / 100.0
                            if opacity < 1.0 and img.mode == 'RGBA':
                                alpha = img.split()[-1]
                                alpha = alpha.point(lambda p: p * opacity)
                                img.putalpha(alpha)
                            
                            # 아웃라인 처리 (고해상도에 맞춰 스케일링)
                            if annotation.get('outline', False):
                                outline_width = int(annotation.get('outline_width', 3) * quality_multiplier)
                                outline_width = max(2, outline_width)  # 최소 두께 보장
                                new_size = (img.width + outline_width * 2, 
                                           img.height + outline_width * 2)
                                outlined_image = Image.new('RGBA', new_size, (0, 0, 0, 0))
                                
                                # 🔥 더 부드러운 아웃라인 그리기 (안티앨리어싱 효과)
                                for dx in range(-outline_width, outline_width + 1):
                                    for dy in range(-outline_width, outline_width + 1):
                                        distance = math.sqrt(dx*dx + dy*dy)
                                        if distance <= outline_width:
                                            # 거리에 따른 알파값 조정으로 부드러운 아웃라인
                                            alpha_factor = 1.0 - (distance / outline_width) * 0.3
                                            alpha_factor = max(0.7, min(1.0, alpha_factor))
                                            outline_color = (255, 255, 255, int(255 * alpha_factor))
                                            outlined_image.paste(outline_color, 
                                                               (outline_width + dx, outline_width + dy),
                                                               img)
                                
                                # 원본 이미지 중앙에 붙이기
                                outlined_image.paste(img, (outline_width, outline_width), img if img.mode == 'RGBA' else None)
                                img = outlined_image
                                # 좌표 조정은 실제 출력 크기 기준으로
                                x -= (outline_width * width / high_res_width)
                                y -= (outline_width * height / high_res_height)
                            
                            # 🔥 고품질 임시 파일로 이미지 저장 후 PDF에 그리기
                            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                                # RGB 모드로 변환 (PDF 호환성)
                                if img.mode == 'RGBA':
                                    # 투명한 배경을 흰색으로 변환 (고품질 알파 블렌딩)
                                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                                    if opacity < 1.0:
                                        # 투명도가 있는 경우 고품질 알파 블렌딩
                                        rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                    else:
                                        rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                    img = rgb_img
                                elif img.mode != 'RGB':
                                    img = img.convert('RGB')
                                
                                # 🔥 최고 품질로 저장 (압축 없음, 최적화 없음)
                                img.save(tmp_file.name, format='PNG', 
                                        optimize=False, compress_level=0, 
                                        pnginfo=None)  # 메타데이터 제거로 용량 최적화
                                
                                # PDF 좌표계에 맞춰 y 위치 조정
                                pdf_y = y - height
                                
                                # 🔥 고해상도 이미지를 원하는 크기로 출력 (품질 유지)
                                canvas.drawImage(tmp_file.name, x, pdf_y, width, height, 
                                               preserveAspectRatio=True, anchor='sw')
                                
                                try:
                                    os.unlink(tmp_file.name)
                                except:
                                    pass
                        
                        except Exception as e:
                            logger.debug(f"PDF 이미지 주석 그리기 오류: {e}")
                
                except Exception as e:
                    logger.debug(f"개별 벡터 주석 그리기 오류: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"벡터 주석 그리기 오류: {e}")
    
    def _fallback_pdf_page(self, canvas, item, index, page_width, page_height):
        """폴백 PDF 페이지 생성 - 하단 여백 축소"""
        try:
            combined_image = self.create_high_quality_combined_image(item)
            
            margin = 50
            max_width = page_width - (margin * 2)
            max_height = page_height - 65  # 🔥 하단 여백 대폭 축소 (기존 100 → 65)
            
            img_ratio = combined_image.width / combined_image.height
            
            if combined_image.width > max_width:
                new_width = max_width
                new_height = max_width / img_ratio
            else:
                new_width = combined_image.width
                new_height = combined_image.height
            
            if new_height > max_height:
                new_height = max_height
                new_width = max_height * img_ratio
            
            if new_width != combined_image.width or new_height != combined_image.height:
                combined_image = combined_image.resize((int(new_width), int(new_height)), 
                                                     Image.Resampling.LANCZOS)
            
            img_buffer = io.BytesIO()
            combined_image.save(img_buffer, format='PNG', optimize=False)
            img_buffer.seek(0)
            
            x_pos = (page_width - new_width) / 2
            y_pos = (page_height - new_height) / 2
            
            canvas.drawImage(ImageReader(img_buffer), x_pos, y_pos, new_width, new_height)
            
            # 🔥 페이지 번호 계산 (첫장 제외 시 조정)
            skip_title = getattr(self.app, 'skip_title_page', False) if self.app else False
            page_number = index + 1 if skip_title else index + 2
            
            canvas.setFont('Helvetica', 9)
            canvas.drawString(page_width - 80, 15, f"{page_number}")  # 페이지 번호 더 아래로 (20 → 15)
            
        except Exception as e:
            logger.error(f"폴백 PDF 페이지 생성 오류: {e}")
    
    def _add_feedback_text_to_pdf(self, canvas, item, index, y_position, text_area_height, page_width, margin):
        """PDF에 피드백 텍스트 추가 - 스마트 폰트 크기 적용"""
        try:
            feedback_text = item.get('feedback_text', '').strip()
            if not feedback_text:
                return
            
            korean_font = self.font_manager.register_pdf_font()
            
            # 기본 배경 박스 (원래대로 복구)
            canvas.setStrokeColorRGB(0.8, 0.8, 0.8)
            canvas.setFillColorRGB(0.98, 0.98, 0.98)
            canvas.rect(margin, y_position - text_area_height, 
                       page_width - (margin * 2), text_area_height, 
                       stroke=1, fill=1)
            
            # 제목 (원래대로 복구)
            canvas.setFillColorRGB(0.2, 0.2, 0.2)
            canvas.setFont(korean_font, 14)
            
            title_parts = []
            if self.app and hasattr(self.app, 'show_index_numbers') and self.app.show_index_numbers.get():
                title_parts.append(f"#{index + 1}")
            
            if self.app and hasattr(self.app, 'show_name') and self.app.show_name.get():
                title_parts.append(item.get('name', f'피드백 #{index + 1}'))
            
            if self.app and hasattr(self.app, 'show_timestamp') and self.app.show_timestamp.get():
                title_parts.append(f"({item.get('timestamp', '')})")
            
            title_text = " ".join(title_parts) if title_parts else f"피드백 #{index + 1}"
            
            title_y = y_position - 25
            canvas.drawString(margin + 10, title_y, f"💬 {title_text}")
            
            # 텍스트 영역
            canvas.setFillColorRGB(0.1, 0.1, 0.1)
            max_text_width = page_width - (margin * 2) - 20
            
            # 🔥 스마트 폰트 크기 자동 조정 (핵심 개선사항)
            available_height = text_area_height - 45  # 하단 여백 축소 (60 → 45)
            
            # 🔥 피드백 텍스트 폰트 크기 증가 - 최소치 상향 조정
            text_length = len(feedback_text)
            if text_length < 100:
                initial_font_size = 14  # 짧은 텍스트 (11→14)
            elif text_length < 300:
                initial_font_size = 13  # 중간 텍스트 (10→13)
            elif text_length < 600:
                initial_font_size = 12  # 긴 텍스트 (9→12)
            else:
                initial_font_size = 11  # 매우 긴 텍스트 (8→11)
            
            # 최적 폰트 크기 찾기
            best_font_size = initial_font_size
            best_line_height = 18  # 줄 간격도 조금 증가 (16→18)
            
            for font_size in range(initial_font_size, 10, -1):  # 최소 10까지 (7→10)
                canvas.setFont(korean_font, font_size)
                text_lines = self._wrap_text_for_pdf(feedback_text, max_text_width, korean_font, font_size, canvas)
                line_height = font_size + 5  # 적절한 줄 간격
                total_height = len(text_lines) * line_height
                
                if total_height <= available_height:
                    best_font_size = font_size
                    best_line_height = line_height
                    break
            
            # 최종 텍스트 렌더링
            canvas.setFont(korean_font, best_font_size)
            text_lines = self._wrap_text_for_pdf(feedback_text, max_text_width, korean_font, best_font_size, canvas)
            max_lines = int(available_height / best_line_height)
            
            text_y = title_y - 30
            
            for i, line in enumerate(text_lines):
                if i >= max_lines:
                    break
                if text_y < y_position - text_area_height + 2:  # 하단 여백 절반으로 축소 (5 → 2)
                    break
                canvas.drawString(margin + 15, text_y, line)
                text_y -= best_line_height
            
            # 텍스트가 잘렸을 때 표시
            if len(text_lines) > max_lines:
                canvas.setFont(korean_font, max(7, best_font_size - 1))
                canvas.setFillColorRGB(0.5, 0.5, 0.5)
                canvas.drawString(margin + 15, text_y + best_line_height, "... (내용이 더 있습니다)")
                
            logger.debug(f"스마트 폰트 적용: {best_font_size}pt, {len(text_lines)}줄")
        
        except Exception as e:
            logger.error(f"PDF 텍스트 추가 오류: {e}")
    
    def _wrap_text_for_pdf(self, text, max_width, font_name, font_size, canvas):
        """PDF용 텍스트 줄바꿈"""
        try:
            lines = []
            paragraphs = text.split('\n')
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    lines.append("")
                    continue
                
                words = paragraph.split()
                current_line = ""
                
                for word in words:
                    test_line = current_line + " " + word if current_line else word
                    
                    try:
                        text_width = canvas.stringWidth(test_line, font_name, font_size)
                        if text_width <= max_width:
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                            
                            if canvas.stringWidth(current_line, font_name, font_size) > max_width:
                                while current_line and canvas.stringWidth(current_line, font_name, font_size) > max_width:
                                    if len(current_line) > 1:
                                        lines.append(current_line[:-1] + "-")
                                        current_line = current_line[-1:]
                                    else:
                                        break
                    except:
                        if len(test_line) <= 50:
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                
                if current_line:
                    lines.append(current_line)
            
            return lines
            
        except Exception as e:
            logger.debug(f"텍스트 줄바꿈 오류: {e}")
            return [text[i:i+50] for i in range(0, len(text), 50)]

    def create_high_quality_combined_image_transparent(self, canvas, item, index, page_width, page_height):
        """투명도를 지원하는 합성 이미지 생성"""
        try:
            # 투명도를 완벽히 지원하는 합성 이미지 생성
            combined_image = self.create_high_quality_combined_image_with_transparency(item)
            
            # PDF에 추가
            margin = 50
            max_width = page_width - (margin * 2)
            max_height = page_height - 100
            
            img_ratio = combined_image.width / combined_image.height
            
            # 크기 계산
            if combined_image.width > max_width:
                new_width = max_width
                new_height = max_width / img_ratio
            else:
                new_width = combined_image.width
                new_height = combined_image.height
            
            if new_height > max_height:
                new_height = max_height
                new_width = max_height * img_ratio
            
            # 투명도를 유지한 채로 PNG 저장
            img_buffer = io.BytesIO()
            if combined_image.mode == 'RGBA':
                combined_image.save(img_buffer, format='PNG', optimize=False)
            else:
                combined_image.save(img_buffer, format='PNG', optimize=False)
            img_buffer.seek(0)
            
            x_pos = (page_width - new_width) / 2
            y_pos = (page_height - new_height) / 2
            
            # ReportLab은 PNG의 투명도를 자동으로 지원
            canvas.drawImage(ImageReader(img_buffer), x_pos, y_pos, new_width, new_height)
            
            logger.info(f"투명도 지원 PDF 페이지 생성 완료: {combined_image.mode}")
            
        except Exception as e:
            logger.error(f"투명도 지원 합성 오류: {e}")
            # 폴백
            self._fallback_pdf_page(canvas, item, index, page_width, page_height)

    def create_high_quality_combined_image_with_transparency(self, item):
        """투명도를 완벽히 지원하는 합성 이미지 생성"""
        try:
            original_image = item['image'].copy()
            annotations = item.get('annotations', [])
            
            # 투명도가 있는 주석이 있는지 확인
            has_transparency = any(
                ann.get('type') == 'image' and ann.get('opacity', 100) < 100
                for ann in annotations
            )
            
            if has_transparency:
                # RGBA 모드로 변환하여 투명도 지원
                if original_image.mode != 'RGBA':
                    original_image = original_image.convert('RGBA')
                
                # 투명 캔버스 생성
                final_image = Image.new('RGBA', original_image.size, (0, 0, 0, 0))
                final_image.paste(original_image, (0, 0))
                
                # PIL ImageDraw 사용
                draw = ImageDraw.Draw(final_image)
                
                # 투명도를 지원하는 주석 그리기
                for annotation in annotations:
                    if annotation.get('type') == 'image':
                        self._draw_transparent_image_annotation(final_image, annotation)
                    else:
                        # 다른 주석들은 기존 방식
                        self._draw_high_quality_annotation(draw, annotation, original_image.size)
                
                return final_image
            else:
                # 투명도가 없으면 기존 방식
                return self.create_high_quality_combined_image(item)
                
        except Exception as e:
            logger.error(f"투명도 지원 합성 이미지 생성 오류: {e}")
            return self.create_high_quality_combined_image(item)

    def _draw_transparent_image_annotation(self, base_image, annotation):
        """투명도를 완벽 지원하는 이미지 주석 그리기"""
        try:
            x = int(annotation['x'])
            y = int(annotation['y'])
            width = int(annotation['width'])
            height = int(annotation['height'])
            
            # base64 이미지 디코딩
            image_data = base64.b64decode(annotation['image_data'])
            img = Image.open(io.BytesIO(image_data))
            
            # 변형 적용
            if annotation.get('flip_horizontal', False):
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if annotation.get('flip_vertical', False):
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            
            rotation = annotation.get('rotation', 0)
            if rotation != 0:
                img = img.rotate(-rotation, expand=True)
            
            # 크기 조정
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            
            # 🔥 핵심: 투명도 적용 (흰색 배경과 합성하지 않음!)
            opacity = annotation.get('opacity', 100) / 100.0
            logger.info(f"🎨 투명도 처리: {opacity*100:.1f}%")
            
            if opacity < 1.0:
                # RGBA 모드로 변환
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # 🔥 중요: 기존 알파 채널에 투명도 곱하기 (흰색 배경과 합성 안함!)
                r, g, b, a = img.split()
                # 알파 채널에 투명도 곱하기
                new_alpha = a.point(lambda p: int(p * opacity))
                img = Image.merge('RGBA', (r, g, b, new_alpha))
                
                logger.info(f"✅ 투명도 {opacity*100:.1f}% 적용 완료 (RGBA 모드 유지)")
            else:
                # 100% 불투명이면 RGBA로만 변환
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                logger.debug("투명도 100%: RGBA 변환만 수행")
            
            # 아웃라인 처리 (RGBA 모드에서)
            if annotation.get('outline', False):
                outline_width = annotation.get('outline_width', 3)
                new_size = (img.width + outline_width * 2, 
                           img.height + outline_width * 2)
                
                # RGBA 배경으로 아웃라인 이미지 생성
                outlined_image = Image.new('RGBA', new_size, (0, 0, 0, 0))
                
                # 🔥 흰색 아웃라인 그리기 (ImageDraw 방식으로 완전히 개선)
                from PIL import ImageDraw
                draw = ImageDraw.Draw(outlined_image)
                
                # 중앙 위치 계산
                center_x = outline_width
                center_y = outline_width
                
                # 여러 겹의 흰색 테두리 생성 (UI 다이얼로그와 동일 방식)
                for i in range(outline_width):
                    # 바깥쪽부터 안쪽까지 흰색 테두리
                    alpha_factor = max(0.7, 1.0 - (i / outline_width) * 0.3)
                    outline_alpha = int(255 * alpha_factor * opacity)
                    
                    # 흰색 테두리 색상 (투명도 고려)
                    border_color = (255, 255, 255, outline_alpha)
                    
                    # 테두리 좌표 계산
                    left = center_x - outline_width + i
                    top = center_y - outline_width + i  
                    right = center_x + img.width + outline_width - i - 1
                    bottom = center_y + img.height + outline_width - i - 1
                    
                    # 테두리 그리기 (완전한 사각형 테두리)
                    draw.rectangle([left, top, right, bottom], outline=border_color, width=1)
                
                logger.debug(f"🔥 ImageDraw 흰색 아웃라인 완료: 두께 {outline_width}px, 투명도 {opacity:.2f}")
                
                # 원본 이미지를 중앙에 붙이기 (RGBA로 완전 투명도 지원)
                outlined_image.paste(img, (outline_width, outline_width), img)
                img = outlined_image
                x -= outline_width
                y -= outline_width
                
                logger.debug(f"아웃라인 적용 완료: 두께 {outline_width}px, 최종 크기 {img.size}")
            
            # 🔥 핵심: RGBA 이미지를 RGBA 베이스에 투명도와 함께 붙이기
            if base_image.mode == 'RGBA' and img.mode == 'RGBA':
                # 완벽한 알파 블렌딩
                base_image.paste(img, (x, y), img)  # 세 번째 인자가 마스크
                logger.info(f"✅ 투명도 {opacity*100:.1f}% 이미지 RGBA 합성 완료: 위치({x}, {y}), 크기{img.size}")
            else:
                logger.warning(f"⚠️ 모드 불일치: base={base_image.mode}, img={img.mode}")
                if img.mode == 'RGBA':
                    base_image.paste(img, (x, y), img)
                else:
                    base_image.paste(img, (x, y))
            
        except Exception as e:
            logger.error(f"투명도 이미지 주석 그리기 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def create_transparent_pdf_page(self, canvas, item, index, page_width, page_height):
        """투명도를 지원하는 PDF 페이지 생성"""
        try:
            logger.info(f"🎨 투명도 지원 PDF 페이지 생성 시작: {index+1}")
            
            # 🔥 투명도를 완벽히 지원하는 합성 이미지 생성
            combined_image = self.create_high_quality_combined_image_with_transparency(item)
            
            # 페이지 레이아웃 계산
            margin = 50
            feedback_text = item.get('feedback_text', '').strip()
            text_area_height = 0
            
            if feedback_text:
                # 텍스트 영역 높이 계산
                korean_font = self.font_manager.register_pdf_font()
                max_text_width = page_width - 100
                text_lines = self._wrap_text_for_pdf(feedback_text, max_text_width, korean_font, 11, canvas)
                line_height = 18
                title_space = 30  # 제목 공간 대폭 축소 (60 → 30)
                text_area_height = max(60, len(text_lines) * line_height + title_space + 20)  # 최소값 절반 축소 (120 → 60), 여백 절반 축소 (40 → 20)
                max_text_height = page_height * 0.4
                if text_area_height > max_text_height:
                    text_area_height = max_text_height
            
            # 이미지 영역 계산
            image_text_gap = 25
            usable_height = page_height - (margin * 2) - 60 - text_area_height - image_text_gap
            usable_width = page_width - (margin * 2)
            
            # 이미지 크기 조정
            img_ratio = combined_image.width / combined_image.height
            
            if combined_image.width > usable_width or combined_image.height > usable_height:
                if img_ratio > (usable_width / usable_height):
                    new_width = usable_width
                    new_height = usable_width / img_ratio
                else:
                    new_height = usable_height
                    new_width = usable_height * img_ratio
            else:
                new_width = combined_image.width
                new_height = combined_image.height
            
            # 이미지 위치 계산
            img_x = (page_width - new_width) / 2
            img_y = page_height - margin - new_height - 10
            
            # 🔥 핵심: PNG로 저장하여 투명도 유지
            logger.info(f"🎨 이미지 모드: {combined_image.mode}, 크기: {combined_image.size}")
            
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                # RGBA 모드면 PNG로 저장 (투명도 유지)
                if combined_image.mode == 'RGBA':
                    combined_image.save(tmp_file.name, format='PNG', optimize=False)
                    logger.info("✅ RGBA 이미지를 PNG로 저장 (투명도 유지)")
                else:
                    # RGB 모드면 고품질 PNG로 저장
                    high_res_width = int(new_width * 2)
                    high_res_height = int(new_height * 2)
                    if high_res_width != combined_image.width or high_res_height != combined_image.height:
                        combined_image = combined_image.resize((high_res_width, high_res_height), Image.Resampling.LANCZOS)
                    combined_image.save(tmp_file.name, format='PNG', optimize=False)
                    logger.info("✅ RGB 이미지를 고품질 PNG로 저장")
                
                # 🔥 ReportLab에서 PNG 투명도 지원
                canvas.drawImage(tmp_file.name, img_x, img_y, new_width, new_height, preserveAspectRatio=True)
                logger.info(f"✅ 투명도 지원 이미지 PDF 추가 완료: 위치({img_x:.1f}, {img_y:.1f}), 크기({new_width:.1f}x{new_height:.1f})")
                
                try:
                    os.unlink(tmp_file.name)
                except:
                    pass
            
            # 피드백 텍스트 추가
            if feedback_text:
                text_start_y = img_y - image_text_gap
                self._add_feedback_text_to_pdf(canvas, item, index, text_start_y, text_area_height, page_width, margin)
            
            # 꼬리말 및 페이지 번호
            if self.app and hasattr(self.app, 'project_footer') and self.app.project_footer.get():
                show_footer = True
                if hasattr(self.app, 'footer_first_page_only') and self.app.footer_first_page_only.get():
                    # 🔥 제목 페이지가 있을 때는 피드백 페이지에서 꼬리말 출력하지 않음
                    skip_title = getattr(self.app, 'skip_title_page', False)
                    if skip_title:
                        show_footer = (index == 0)  # 제목 페이지가 없으면 첫 번째 피드백 페이지에만 표시
                    else:
                        show_footer = False  # 제목 페이지가 있으면 피드백 페이지에서는 꼬리말 출력하지 않음
                
                if show_footer:
                    korean_font = self.font_manager.register_pdf_font()
                    canvas.setFont(korean_font, 10)
                    footer_text = self.app.project_footer.get().strip()
                    footer_width = canvas.stringWidth(footer_text, korean_font, 10)
                    canvas.drawString((page_width - footer_width) / 2, 15, footer_text)  # 꼬리말 더 아래로 (25 → 15)
            
            # 🔥 페이지 번호 계산 (첫장 제외 시 조정)
            skip_title = getattr(self.app, 'skip_title_page', False)
            page_number = index + 1 if skip_title else index + 2
            
            canvas.setFont('Helvetica', 10)
            canvas.drawString(page_width - 80, 15, f"- {page_number} -")  # 페이지 번호 더 아래로 (25 → 15)
            
            logger.info(f"🎨 투명도 지원 PDF 페이지 {index+1} 생성 완료")
            
        except Exception as e:
            logger.error(f"투명도 지원 PDF 페이지 생성 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 폴백
            self._fallback_pdf_page(canvas, item, index, page_width, page_height)

class CanvasNavigationBar:
    """캔버스 네비게이션 바 클래스"""
    def __init__(self, parent, app_instance):
        self.parent = parent
        self.app = app_instance
        self.canvas = None
        self.minimap_items = []
        self.current_viewport = None
        self.nav_width = 180  # 120 -> 180으로 확대
        self.nav_height = 350  # 300 -> 350으로 확대
        self.item_height = 50  # 40 -> 50으로 확대
        self.margin = 8  # 5 -> 8로 확대
        
        self.create_navigation_bar()
        
    def create_navigation_bar(self):
        """네비게이션 바 생성"""
        # 네비게이션 프레임 - 메인 UI와 일관성 있는 스타일 (좌우 여백 균등)
        self.nav_frame = tk.LabelFrame(self.parent, text="네비게이션", 
                                      bg='white', 
                                      font=self.app.font_manager.ui_font_bold,
                                      fg='#333',
                                      relief='flat', bd=1, highlightbackground='#e0e0e0', 
                                      highlightthickness=1,
                                      padx=6, pady=8,  # 좌우 패딩 조정
                                      width=self.nav_width)
        self.nav_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 8), pady=0)  # 좌우 여백 균등하게
        self.nav_frame.pack_propagate(False)
        
        # 상단 정보 라벨 - 통일된 폰트 사용
        self.info_label = tk.Label(self.nav_frame, text="총 0개", 
                                  bg='white', fg='#495057',
                                  font=self.app.font_manager.ui_font)
        self.info_label.pack(pady=(0, 8))
        
        # 미니맵 캔버스 컨테이너
        canvas_container = tk.Frame(self.nav_frame, bg='white')
        canvas_container.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        # 미니맵 캔버스 - 선택시에도 회색 테두리 유지
        self.canvas = tk.Canvas(canvas_container, bg='#ced4da', 
                               highlightthickness=1, 
                               highlightbackground='#6c757d',
                               highlightcolor='#6c757d',
                               relief='flat', bd=1,
                               width=self.nav_width-28,  # 좌우 여백을 위한 공간 확보
                               height=self.nav_height)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 4))  # 좌우 여백 균등하게
        
        # 스크롤바 - 메인 UI와 일관성 있는 크기
        scrollbar = tk.Scrollbar(canvas_container, orient=tk.VERTICAL, 
                                command=self.canvas.yview, width=20)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # 이벤트 바인딩
        self.canvas.bind('<Button-1>', self.on_minimap_click)
        self.canvas.bind('<MouseWheel>', self.on_minimap_scroll)
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        # 하단 컨트롤 프레임
        control_frame = tk.Frame(self.nav_frame, bg='white')
        control_frame.pack(fill=tk.X, pady=(0, 0))
        
        # 이전/다음 버튼 컨테이너
        btn_frame = tk.Frame(control_frame, bg='white')
        btn_frame.pack(expand=True)
        
        # 이전/다음 버튼 - 화살표만 표시 (더 작은 크기)
        button_style = {
            'bg': 'white', 'fg': '#2196F3',
            'relief': 'flat', 'bd': 0,
            'activebackground': '#e3f2fd',
            'activeforeground': '#2196F3',
            'font': ('Malgun Gothic', 10, 'bold'),  # 14 -> 10으로 폰트 크기 축소
            'width': 2, 'height': 1,  # 3 -> 2로 버튼 너비 축소
            'padx': 3, 'pady': 2  # 6,4 -> 3,2로 패딩 축소
        }
        
        self.prev_btn = tk.Button(btn_frame, text="◀", command=self.go_previous, **button_style)
        self.prev_btn.pack(side=tk.LEFT, padx=3)
        
        self.next_btn = tk.Button(btn_frame, text="▶", command=self.go_next, **button_style)
        self.next_btn.pack(side=tk.LEFT, padx=3)
        
    def refresh_minimap(self):
        """미니맵 새로고침"""
        if not self.canvas:
            return
            
        self.canvas.delete("all")
        self.minimap_items.clear()
        
        if not self.app.feedback_items:
            self.info_label.config(text="📄 피드백 없음", fg='#6c757d')
            self.update_navigation_buttons()
            return
            
        total_items = len(self.app.feedback_items)
        current_pos = self.app.current_index + 1
        self.info_label.config(text=f"📊 총 {total_items}개 | 현재 {current_pos}번째", fg='#495057')
        
        # 미니맵 아이템 그리기
        canvas_width = self.canvas.winfo_width() or (self.nav_width - 25)
        y_pos = self.margin
        
        for i, item in enumerate(self.app.feedback_items):
            # 현재 선택된 항목 표시
            is_current = (i == self.app.current_index)
            
            # 개선된 색상 스키마
            if is_current:
                bg_color = '#2196F3'  # 메인 UI와 일관성 있는 파란색
                text_color = 'white'
                border_color = '#1976D2'
                shadow_color = '#e3f2fd'
            else:
                bg_color = '#ffffff'
                text_color = '#333333'
                border_color = '#dee2e6'
                shadow_color = '#f8f9fa'
            
            # 미니맵 아이템 그리기 - 더 큰 영역
            x1, y1 = self.margin, y_pos
            x2, y2 = canvas_width - self.margin, y_pos + self.item_height
            
            # 그림자 효과 (선택된 항목만)
            if is_current:
                shadow_rect = self.canvas.create_rectangle(x1 + 2, y1 + 2, x2 + 2, y2 + 2,
                                                         fill=shadow_color, outline='', width=0)
            
            # 배경 사각형 - 둥근 모서리 효과
            rect_id = self.canvas.create_rectangle(x1, y1, x2, y2,
                                                  fill=bg_color, outline=border_color,
                                                  width=2 if is_current else 1)
            
            # 텍스트 (이름) - 더 큰 글자와 적절한 길이
            text = item.get('name', f'피드백 {i+1}')
            if len(text) > 18:  # 12 -> 18로 확장
                text = text[:18] + '...'
                
            # 메인 제목 - 더 큰 폰트
            text_id = self.canvas.create_text(x1 + 8, y1 + 8, text=text,
                                            anchor='nw', fill=text_color,
                                            font=('Malgun Gothic', 10, 'bold' if is_current else 'normal'))
            
            # 주석 개수 표시 - 개선된 위치와 스타일
            annotation_count = len(item.get('annotations', []))
            if annotation_count > 0:
                count_text = f"📝 {annotation_count}개"
                self.canvas.create_text(x2 - 8, y1 + 8, text=count_text,
                                      anchor='ne', fill=text_color,
                                      font=('Malgun Gothic', 8))
            
            # 인덱스 정보 표시
            index_text = f"#{i+1}"
            self.canvas.create_text(x1 + 8, y2 - 8, text=index_text,
                                  anchor='sw', fill=text_color,
                                  font=('Malgun Gothic', 9, 'bold'))
            
            # 미니맵 아이템 정보 저장
            self.minimap_items.append({
                'index': i,
                'rect_id': rect_id,
                'bounds': (x1, y1, x2, y2)
            })
            
            y_pos += self.item_height + self.margin
        
        # 스크롤 영역 설정
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # 네비게이션 버튼 상태 업데이트
        self.update_navigation_buttons()
        
        # 현재 항목으로 스크롤
        self.scroll_to_current()
        
    def on_minimap_click(self, event):
        """미니맵 클릭 이벤트"""
        canvas_y = self.canvas.canvasy(event.y)
        
        for item in self.minimap_items:
            x1, y1, x2, y2 = item['bounds']
            if y1 <= canvas_y <= y2:
                # 선택된 피드백으로 이동
                self.app.current_index = item['index']
                self.app.scroll_to_card(item['index'])
                self.app.update_status()
                self.refresh_minimap()
                break
                
    def on_minimap_scroll(self, event):
        """미니맵 스크롤 이벤트"""
        self.canvas.yview_scroll(int(1 * (event.delta / 120)), "units")
        
    def on_canvas_configure(self, event):
        """캔버스 크기 변경 이벤트"""
        # 크기 변경시 미니맵 새로고침 (너무 자주 호출되지 않도록 딜레이)
        if hasattr(self, '_refresh_timer'):
            self.app.root.after_cancel(self._refresh_timer)
        self._refresh_timer = self.app.root.after(100, self.refresh_minimap)
        
    def scroll_to_current(self):
        """현재 선택된 항목으로 스크롤"""
        if not self.minimap_items or self.app.current_index >= len(self.minimap_items):
            return
            
        current_item = self.minimap_items[self.app.current_index]
        x1, y1, x2, y2 = current_item['bounds']
        
        # 캔버스의 현재 보이는 영역
        canvas_height = self.canvas.winfo_height()
        if canvas_height <= 1:
            return
            
        top = self.canvas.canvasy(0)
        bottom = top + canvas_height
        
        # 현재 항목이 보이지 않으면 스크롤
        if y1 < top or y2 > bottom:
            # 항목을 중앙에 위치시키기
            target_y = max(0, y1 - canvas_height // 2)
            bbox = self.canvas.bbox("all")
            if bbox:
                total_height = bbox[3] - bbox[1]
                if total_height > 0:
                    fraction = target_y / total_height
                    self.canvas.yview_moveto(fraction)
                
    def go_previous(self):
        """이전 피드백으로 이동"""
        if self.app.current_index > 0:
            self.app.current_index -= 1
            self.app.scroll_to_card(self.app.current_index)
            self.app.update_status()
            self.refresh_minimap()
            
    def go_next(self):
        """다음 피드백으로 이동"""
        if self.app.current_index < len(self.app.feedback_items) - 1:
            self.app.current_index += 1
            self.app.scroll_to_card(self.app.current_index)
            self.app.update_status()
            self.refresh_minimap()
            
    def update_navigation_buttons(self):
        """네비게이션 버튼 상태 업데이트"""
        if hasattr(self, 'prev_btn') and hasattr(self, 'next_btn'):
            # 이전 버튼
            if self.app.current_index <= 0 or not self.app.feedback_items:
                self.prev_btn.config(state='disabled', 
                                    bg='#f8f9fa', fg='#adb5bd',
                                    relief='flat', bd=0)
            else:
                self.prev_btn.config(state='normal',
                                    bg='white', fg='#2196F3',
                                    relief='flat', bd=0)
                
            # 다음 버튼
            if (self.app.current_index >= len(self.app.feedback_items) - 1 or 
                not self.app.feedback_items):
                self.next_btn.config(state='disabled',
                                    bg='#f8f9fa', fg='#adb5bd',
                                    relief='flat', bd=0)
            else:
                self.next_btn.config(state='normal',
                                    bg='white', fg='#2196F3',
                                    relief='solid', bd=0)

class PDFInfoDialog:
    """PDF 정보 입력 다이얼로그 - 페이지 크기 옵션 추가"""
    
    def __init__(self, parent, app_instance):
        self.parent = parent
        self.app = app_instance
        self.result = None
        self.dialog = None
        self.desc_text = None
        
        # 현재 값들을 가져와서 기본값으로 설정
        self.project_title = tk.StringVar(value=app_instance.project_title.get())
        self.project_to = tk.StringVar(value=app_instance.project_to.get())
        self.project_from = tk.StringVar(value=app_instance.project_from.get())
        self.project_description = tk.StringVar(value=app_instance.project_description.get())
        self.project_footer = tk.StringVar(value=app_instance.project_footer.get())
        self.footer_first_page_only = tk.BooleanVar(value=app_instance.footer_first_page_only.get())
        
        # 🔥 새로운 페이지 크기 옵션 추가
        self.pdf_page_mode = tk.StringVar(value=getattr(app_instance, 'pdf_page_mode', 'A4'))
        
        # PDF 가독성 내보내기 옵션
        self.pdf_readability_mode = tk.BooleanVar(value=False)
        
        # 🔥 첫장 제외하기 옵션 추가
        self.skip_title_page = tk.BooleanVar(value=getattr(app_instance, 'skip_title_page', False))
        
        self.create_dialog()
    
    def create_dialog(self):
        """PDF 정보 입력 대화상자 생성"""
        try:
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title("PDF 내보내기 설정")
            
            # 🔥 화면 해상도에 따른 적응형 크기 설정
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            # 기본 크기 계산 (화면 크기의 40% 너비, 80% 높이, 최소/최대 제한)
            dialog_width = max(600, min(800, int(screen_width * 0.4)))
            dialog_height = max(600, min(1000, int(screen_height * 0.8)))
            
            self.dialog.geometry(f"{dialog_width}x{dialog_height}")
            self.dialog.resizable(True, True)  # 🔥 크기 조정 가능
            self.dialog.minsize(550, 500)      # 🔥 최소 크기 설정
            self.dialog.maxsize(1000, int(screen_height * 0.9))  # 🔥 최대 크기 설정
            self.dialog.configure(bg='white')

            # 🔥 스크롤 가능한 메인 프레임 생성
            canvas_frame = tk.Frame(self.dialog, bg='white')
            canvas_frame.pack(fill=tk.BOTH, expand=True)
            
            # 캔버스와 스크롤바
            main_canvas = tk.Canvas(canvas_frame, bg='white', highlightthickness=0)
            scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=main_canvas.yview)
            self.scrollable_main_frame = tk.Frame(main_canvas, bg='white')
            
            # 스크롤바 설정
            self.scrollable_main_frame.bind(
                "<Configure>",
                lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
            )
            
            main_canvas.create_window((0, 0), window=self.scrollable_main_frame, anchor="nw")
            main_canvas.configure(yscrollcommand=scrollbar.set)
            
            # 마우스 휠 스크롤 지원
            def _on_mousewheel(event):
                main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            main_canvas.bind("<MouseWheel>", _on_mousewheel)
            
            # 스크롤바와 캔버스 배치
            main_canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # 실제 콘텐츠가 들어갈 프레임
            main_frame = tk.Frame(self.scrollable_main_frame, bg='white')
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            # 제목 섹션 (기존과 동일)
            title_section = tk.LabelFrame(main_frame, text="문서 정보", bg='white', 
                                        font=self.app.font_manager.ui_font)
            title_section.pack(fill=tk.X, pady=(0, 15))

            tk.Label(title_section, text="제목:", bg='white', 
                    font=self.app.font_manager.ui_font).pack(anchor=tk.W, padx=10, pady=(10, 5))
            title_entry = tk.Entry(title_section, textvariable=self.project_title, 
                                 font=self.app.font_manager.ui_font, width=60)
            title_entry.pack(fill=tk.X, padx=10, pady=(0, 10))

            # 🔥 페이지 크기 설정 섹션 추가
            size_section = tk.LabelFrame(main_frame, text="페이지 크기 설정", bg='white',
                                       font=self.app.font_manager.ui_font)
            size_section.pack(fill=tk.X, pady=(0, 15))
            
            # 라디오 버튼들
            tk.Radiobutton(size_section, text="📄 A4 고정 (표준, 210×297mm)", 
                          variable=self.pdf_page_mode, value='A4',
                          bg='white', font=self.app.font_manager.ui_font,
                          command=self.update_page_preview).pack(anchor=tk.W, padx=10, pady=5)
            
            tk.Radiobutton(size_section, text="📐 이미지 크기에 맞춤 (권장)", 
                          variable=self.pdf_page_mode, value='adaptive',
                          bg='white', font=self.app.font_manager.ui_font,
                          command=self.update_page_preview).pack(anchor=tk.W, padx=10, pady=5)
            
            # 미리보기 정보
            self.page_preview = tk.Label(size_section, text="", bg='white', fg='#666',
                                       font=(self.app.font_manager.ui_font[0], 9))
            self.page_preview.pack(anchor=tk.W, padx=25, pady=(0, 10))

            # 수신자/발신자 섹션 (기존과 동일)
            sender_section = tk.LabelFrame(main_frame, text="수신자/발신자 정보", bg='white',
                                         font=self.app.font_manager.ui_font)
            sender_section.pack(fill=tk.X, pady=(0, 15))

            tk.Label(sender_section, text="수신:", bg='white',
                    font=self.app.font_manager.ui_font).pack(anchor=tk.W, padx=10, pady=(10, 5))
            to_entry = tk.Entry(sender_section, textvariable=self.project_to,
                              font=self.app.font_manager.ui_font, width=60)
            to_entry.pack(fill=tk.X, padx=10, pady=(0, 10))

            tk.Label(sender_section, text="발신:", bg='white',
                    font=self.app.font_manager.ui_font).pack(anchor=tk.W, padx=10, pady=(0, 5))
            from_entry = tk.Entry(sender_section, textvariable=self.project_from,
                                 font=self.app.font_manager.ui_font, width=60)
            from_entry.pack(fill=tk.X, padx=10, pady=(0, 10))

            # 설명 섹션 (기존과 동일)
            desc_section = tk.LabelFrame(main_frame, text="문서 설명", bg='white',
                                       font=self.app.font_manager.ui_font)
            desc_section.pack(fill=tk.X, pady=(0, 15))

            tk.Label(desc_section, text="설명:", bg='white',
                    font=self.app.font_manager.ui_font).pack(anchor=tk.W, padx=10, pady=(10, 5))
            
            desc_container = tk.Frame(desc_section, bg='white')
            desc_container.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            self.desc_text = tk.Text(desc_container, height=6, width=60, wrap=tk.WORD,
                                   font=self.app.font_manager.ui_font)
            desc_scrollbar = tk.Scrollbar(desc_container, orient=tk.VERTICAL, command=self.desc_text.yview)
            self.desc_text.configure(yscrollcommand=desc_scrollbar.set)
            
            self.desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            desc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            self.desc_text.insert('1.0', self.app.project_description.get())
            self.desc_text.bind('<KeyRelease>', lambda e: self.app.project_description.set(self.desc_text.get('1.0', tk.END).strip()))

            # 꼬리말 섹션 (기존과 동일)
            footer_section = tk.LabelFrame(main_frame, text="꼬리말", bg='white',
                                         font=self.app.font_manager.ui_font)
            footer_section.pack(fill=tk.X, pady=(0, 15))

            tk.Label(footer_section, text="꼬리말:", bg='white',
                    font=self.app.font_manager.ui_font).pack(anchor=tk.W, padx=10, pady=(10, 5))
            
            footer_entry = tk.Entry(footer_section, textvariable=self.project_footer,
                                  font=self.app.font_manager.ui_font, width=60)
            footer_entry.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            footer_option = tk.Checkbutton(footer_section, text="첫 장에만 꼬리말 출력",
                                         variable=self.footer_first_page_only,
                                         bg='white', font=self.app.font_manager.ui_font)
            footer_option.pack(anchor=tk.W, padx=10, pady=(0, 10))

            # 가독성 옵션 섹션
            readability_section = tk.LabelFrame(main_frame, text="가독성 옵션", bg='white',
                                              font=self.app.font_manager.ui_font)
            readability_section.pack(fill=tk.X, pady=(0, 15))
            
            readability_option = tk.Checkbutton(readability_section, 
                                              text="📖 가독성 내보내기 (텍스트 배경 + 주석 흰색 아웃라인)",
                                              variable=self.pdf_readability_mode,
                                              bg='white', font=self.app.font_manager.ui_font)
            readability_option.pack(anchor=tk.W, padx=10, pady=10)
            
            # 설명 텍스트
            readability_desc = tk.Label(readability_section, 
                                      text="※ 복잡한 배경에서 주석의 가독성을 향상시킵니다.",
                                      bg='white', fg='#666', 
                                      font=(self.app.font_manager.ui_font[0], 9))
            readability_desc.pack(anchor=tk.W, padx=25, pady=(0, 10))

            # 🔥 페이지 구성 옵션 섹션 추가
            page_section = tk.LabelFrame(main_frame, text="페이지 구성", bg='white',
                                        font=self.app.font_manager.ui_font)
            page_section.pack(fill=tk.X, pady=(0, 15))
            
            skip_title_option = tk.Checkbutton(page_section, 
                                             text="📄 첫장 제외하기 (제목 페이지 생략)",
                                             variable=self.skip_title_page,
                                             bg='white', font=self.app.font_manager.ui_font)
            skip_title_option.pack(anchor=tk.W, padx=10, pady=10)
            
            # 설명 텍스트
            skip_title_desc = tk.Label(page_section, 
                                     text="※ 제목 페이지 없이 피드백 이미지들만 PDF로 생성됩니다.",
                                     bg='white', fg='#666', 
                                     font=(self.app.font_manager.ui_font[0], 9))
            skip_title_desc.pack(anchor=tk.W, padx=25, pady=(0, 10))

            # 버튼 섹션 (기존과 동일)
            button_frame = tk.Frame(main_frame, bg='white')
            button_frame.pack(fill=tk.X, pady=(20, 0))

            cancel_btn = tk.Button(button_frame, text="취소", command=self.cancel,
                                 font=self.app.font_manager.ui_font,
                                 bg='white', fg='#666666', 
                                 relief='solid', bd=1,
                                 padx=20, pady=8,
                                 activebackground='#f5f5f5',
                                 activeforeground='#666666')
            cancel_btn.pack(side=tk.LEFT)

            export_btn = tk.Button(button_frame, text="PDF 내보내기", command=self.generate_pdf,
                                 font=self.app.font_manager.ui_font,
                                 bg='white', fg='#2196F3',
                                 relief='solid', bd=1,
                                 padx=25, pady=8,
                                 activebackground='#e3f2fd',
                                 activeforeground='#2196F3')
            export_btn.pack(side=tk.RIGHT)

            # 🔥 스마트 창 위치 조정 - 화면 경계 고려
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
            
            self.dialog.update_idletasks()
            dialog_width = self.dialog.winfo_width()
            dialog_height = self.dialog.winfo_height()
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            try:
                parent_x = self.parent.winfo_x()
                parent_y = self.parent.winfo_y()
                parent_width = self.parent.winfo_width()
                parent_height = self.parent.winfo_height()
                
                # 부모 창 중앙 계산
                x = parent_x + (parent_width - dialog_width) // 2
                y = parent_y + (parent_height - dialog_height) // 2
            except tk.TclError:
                # 부모 창 정보를 가져올 수 없는 경우 화면 중앙으로
                x = (screen_width - dialog_width) // 2
                y = (screen_height - dialog_height) // 2
            
            # 화면 경계 확인 및 조정
            margin = 20
            if x + dialog_width > screen_width - margin:
                x = screen_width - dialog_width - margin
            if x < margin:
                x = margin
            if y + dialog_height > screen_height - 60:  # 작업 표시줄 고려
                y = screen_height - dialog_height - 60
            if y < margin:
                y = margin
            
            self.dialog.geometry(f"+{x}+{y}")

            title_entry.focus_set()
            
            # 초기 미리보기 업데이트
            self.update_page_preview()

            # 🔥 아이콘 설정
            setup_window_icon(self.dialog)

        except Exception as e:
            logger.error(f"PDF 정보 대화상자 생성 오류: {e}")
            messagebox.showerror("오류", "PDF 정보 대화상자를 생성하는 중 오류가 발생했습니다.")
    
    def update_page_preview(self):
        """페이지 크기 미리보기 업데이트 - 세로 긴 이미지 정보 포함"""
        try:
            mode = self.pdf_page_mode.get()
            
            if mode == 'A4':
                preview_text = "모든 페이지가 A4 크기(210×297mm)로 생성됩니다."
            else:  # adaptive
                if hasattr(self.app, 'feedback_items') and self.app.feedback_items:
                    total_items = len(self.app.feedback_items)
                    
                    # 🔥 이미지 유형 분석
                    a4_ratio = 210.0 / 297.0  # ≈ 0.707
                    tall_images = 0  # 세로가 긴 이미지 수
                    wide_images = 0  # 가로가 긴 이미지 수
                    normal_images = 0  # 일반 비율 이미지 수
                    
                    for item in self.app.feedback_items:
                        img_w, img_h = item['image'].size
                        img_ratio = img_w / img_h
                        
                        if img_ratio < a4_ratio * 0.8:  # A4보다 훨씬 세로가 긴 이미지
                            tall_images += 1
                        elif img_ratio > a4_ratio * 1.5:  # A4보다 훨씬 가로가 긴 이미지  
                            wide_images += 1
                        else:
                            normal_images += 1
                    
                    # 첫 번째 이미지 크기 예시
                    first_item = self.app.feedback_items[0]
                    img_w, img_h = first_item['image'].size
                    img_ratio = img_w / img_h
                    
                    
                    # 🔥 실제 PDF 생성과 동일한 DPI 사용
                    dpi = getattr(self.app, 'pdf_quality', None)
                    if dpi is None or not hasattr(dpi, 'get'):
                        dpi = 150  # 기본값
                    else:
                        dpi = dpi.get()
                    
                    # 대략적인 페이지 크기 계산 (실제 DPI 사용)
                    page_w_mm = int((img_w / dpi) * 25.4) + 4  # 🔥 여백 통일 (20→4mm)
                    page_h_mm = int((img_h / dpi) * 25.4) + 4
                    
                    # 🔥 세로 긴 이미지에 대한 추가 정보
                    if img_ratio < a4_ratio:
                        is_tall = " (세로 긴 이미지 최적화)"
                    else:
                        is_tall = ""
                    
                    preview_lines = [
                        f"각 이미지 크기에 맞춰 생성됩니다.",
                        f"예시: 첫 번째 이미지 → 약 {page_w_mm}×{page_h_mm}mm{is_tall}",
                        f"총 {total_items}개 페이지"
                    ]
                    
                    # 🔥 이미지 유형별 통계 추가
                    if tall_images > 0 or wide_images > 0:
                        type_info = []
                        if tall_images > 0:
                            type_info.append(f"세로형 {tall_images}개")
                        if normal_images > 0:
                            type_info.append(f"일반형 {normal_images}개")
                        if wide_images > 0:
                            type_info.append(f"가로형 {wide_images}개")
                        
                        preview_lines.append(f"구성: {', '.join(type_info)}")
                    
                    # 🔥 세로 긴 이미지 특별 안내
                    if tall_images > 0:
                        preview_lines.append("※ 세로 긴 이미지는 원본 크기 기준으로 최적화됩니다")
                    
                    preview_text = "\n".join(preview_lines)
                else:
                    preview_text = "이미지별로 최적화된 크기로 생성됩니다.\n※ 세로 긴 이미지는 원본 비율을 유지합니다"
            
            self.page_preview.config(text=preview_text)
            
        except Exception as e:
            logger.debug(f"페이지 미리보기 업데이트 오류: {e}")
    
    def generate_pdf(self):
        """PDF 생성 실행"""
        try:
            # 입력된 정보 수집
            description = self.desc_text.get('1.0', tk.END).strip()
            footer = self.project_footer.get().strip()
            
            self.result = {
                'title': self.project_title.get(),
                'to': self.project_to.get(),
                'from': self.project_from.get(),
                'description': description,
                'footer': footer,
                'footer_first_page_only': self.footer_first_page_only.get(),
                'pdf_page_mode': self.pdf_page_mode.get(),  # 🔥 중요: 페이지 모드 포함
                'pdf_readability_mode': self.pdf_readability_mode.get(),  # 가독성 모드 추가
                'skip_title_page': self.skip_title_page.get()  # 🔥 첫장 제외하기 옵션 추가
            }
            
            # 앱의 설정값들 업데이트
            self.app.project_title.set(self.result['title'])
            self.app.project_to.set(self.result['to'])
            self.app.project_from.set(self.result['from'])
            self.app.project_description.set(self.result['description'])
            self.app.project_footer.set(self.result['footer'])
            self.app.footer_first_page_only.set(self.result['footer_first_page_only'])
            
            # 🔥 중요: 페이지 모드 설정 저장
            self.app.pdf_page_mode = self.result['pdf_page_mode']
            
            # 가독성 모드 설정 저장
            self.app.pdf_readability_mode = self.result['pdf_readability_mode']
            
            # 첫장 제외하기 설정 저장
            self.app.skip_title_page = self.result['skip_title_page']
            
            self.dialog.destroy()
            
            # PDF 생성 시작
            self.app.start_pdf_generation()
            
        except Exception as e:
            logger.error(f"PDF 정보 수집 오류: {e}")
            messagebox.showerror('오류', f'정보 수집 중 오류가 발생했습니다: {str(e)}')
    
    def cancel(self):
        """취소"""
        self.result = None
        self.dialog.destroy()

"""
🎯 악어스튜디오 캡쳐 피드백 도구 V1.6.1 - 배포 최적화 버전
==================================================
- 영역 선택으로 다중 주석 선택/이동/삭제
- PDF 텍스트 주석 완벽 출력 (배경/테두리 제거)
- 빈 캔버스 생성 기능 추가
- UI 레이아웃 최적화
- PDF 정보 입력창 분리
- 모든 기능 디버그 및 최적화 완료

🚀 V1.6.1 배포 최적화:
- 동적 디버그 모드 (--debug 플래그 또는 DEBUG_MODE 환경변수)
- 프로덕션 로그 레벨 최적화 (WARNING 이상만 출력)
- 콘솔 창 자동 숨김 (프로덕션 모드)
- 디버그 출력 완전 제거 (프로덕션 모드)
==================================================
"""

import sys
import os
import threading
import time
import json
import io
import base64
import math
import logging
import traceback
import gc
import tempfile
import platform
import shutil
import weakref
from datetime import datetime
from pathlib import Path
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import subprocess

#  PyInstaller one-file 실행 시 리소스 경로 얻기
def resource_path(rel_path: str) -> str:
    base = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base, rel_path)

# 버전 정보

# 🔥 [중복 제거됨] V1.6.1 블록 #1

# 🔥 [중복 제거됨] V1.6.1 블록 #1
COPYRIGHT = "Copyright 2025 악어스튜디오 INC. All rights reserved."

# 로깅 설정

# 🔥 [중복 제거됨] V1.6.1 블록 #1

logger = setup_logging()

# 시스템 정보 로깅
logger.info("=" * 60)
logger.info(f"악어스튜디오 캡쳐 피드백 도구 V{VERSION}")
logger.info(f"빌드일: {BUILD_DATE}")
logger.info(f"시스템: {platform.system()} {platform.release()}")
logger.info(f"Python: {sys.version}")
logger.info("=" * 60)

# 🔥 [중복 제거됨] 세 번째 V1.6.1 블록 - 상단의 첫 번째 블록으로 통합됨

class SafeThreadExecutor:
    """Thread-safe 작업 실행기"""
    
    def __init__(self, max_workers=2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures = set()
        self._cleanup_completed()
    
    def submit(self, fn, *args, **kwargs):
        """작업 제출"""
        future = self.executor.submit(fn, *args, **kwargs)
        self.futures.add(future)
        return future
    
    def _cleanup_completed(self):
        """완료된 작업 정리"""
        completed = {f for f in self.futures if f.done()}
        self.futures -= completed
    
    def shutdown(self):
        """실행기 종료"""
        self.executor.shutdown(wait=False)

class SystemMonitor:
    """시스템 리소스 모니터링"""
    
    def __init__(self):
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None
        self.memory_warnings = 0
        # 🔥 웹툰 지원: 메모리 제한 대폭 증가 (1GB → 3GB)
        self.max_memory_mb = 3072  # 웹툰과 같은 큰 이미지들을 위해 3GB로 증가
        self._last_memory_check = 0
        self._memory_check_interval = 3  # 체크 간격 단축 (5초 → 3초)
    
    def get_memory_usage(self):
        """현재 메모리 사용량 반환 (MB)"""
        try:
            if self.process:
                current_time = time.time()
                if current_time - self._last_memory_check > self._memory_check_interval:
                    self._last_memory_check = current_time
                    return self.process.memory_info().rss / 1024 / 1024
                return getattr(self, '_cached_memory', 0)
            return 0
        except Exception:
            return 0
    
    def check_memory_limit(self):
        """메모리 제한 확인"""
        current_memory = self.get_memory_usage()
        self._cached_memory = current_memory
        
        if current_memory > self.max_memory_mb:
            self.memory_warnings += 1
            logger.warning(f"메모리 사용량 초과: {current_memory:.1f}MB")
            if self.memory_warnings > 3:
                return False
        return True
    
    def get_disk_space(self, path):
        """디스크 공간 확인 (MB)"""
        try:
            if PSUTIL_AVAILABLE:
                usage = psutil.disk_usage(path)
                return usage.free / 1024 / 1024
            return float('inf')
        except Exception:
            return float('inf')

class AdvancedProgressDialog:
    """향상된 진행 상황 표시 다이얼로그"""
    
    def __init__(self, parent, title, message, auto_close_ms=None, cancelable=False):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("450x180")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.canceled = False
        self.cancel_callback = None
        
        if auto_close_ms:
            self.dialog.after(auto_close_ms, self.close)

        # 창 중앙 배치
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 225
        y = (self.dialog.winfo_screenheight() // 2) - 90
        self.dialog.geometry(f"+{x}+{y}")
        
        # UI 구성
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.message_label = tk.Label(main_frame, text=message, 
                                     font=('맑은 고딕', 11, 'bold'))
        self.message_label.pack(pady=(0, 15))
        
        # 진행률 바와 퍼센트 표시를 함께
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate', length=350)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.percent_label = tk.Label(progress_frame, text="0%", font=('맑은 고딕', 9, 'bold'), width=5)
        self.percent_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.detail_label = tk.Label(main_frame, text="", 
                                    font=('맑은 고딕', 9), fg='#666')
        self.detail_label.pack()
        
        # 취소 버튼 (옵션)
        if cancelable:
            self.cancel_btn = tk.Button(main_frame, text="취소", 
                                       command=self.cancel,
                                       bg='#dc3545', fg='white',
                                       font=('맑은 고딕', 9))
            self.cancel_btn.pack(pady=(10, 0))
        
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel if cancelable else lambda: None)
        self.dialog.update()
    
    def update(self, value, detail=""):
        """진행률 업데이트"""
        try:
            if self.canceled:
                return False
                
            self.progress['value'] = min(100, max(0, value))
            self.percent_label.config(text=f"{int(value)}%")
            
            if detail:
                self.detail_label.config(text=detail)
            self.dialog.update()
            return True
        except Exception:
            return False
    
    def cancel(self):
        """취소 처리"""
        self.canceled = True
        if self.cancel_callback:
            self.cancel_callback()
        self.close()
    
    def set_cancel_callback(self, callback):
        """취소 콜백 설정"""
        self.cancel_callback = callback
    
    def close(self):
        """다이얼로그 닫기"""
        try:
            self.dialog.destroy()
        except Exception:
            pass

class SmartUndoManager:
    """스마트 되돌리기 관리 클래스"""
    
    def __init__(self, max_history=8):
        self.max_history = max_history
        self.histories = {}
        self._last_cleanup = time.time()
    
    def save_state(self, item_id, annotations):
        """현재 주석 상태 저장"""
        try:
            if item_id not in self.histories:
                self.histories[item_id] = deque(maxlen=self.max_history)
            
            state = [ann.copy() for ann in annotations]
            self.histories[item_id].append(state)
            
            if time.time() - self._last_cleanup > 300:
                self._cleanup_old_histories()
                
            logger.debug(f"상태 저장됨 - Item {item_id}: {len(state)}개 주석")
            
        except Exception as e:
            logger.error(f"상태 저장 오류: {e}")
    
    def undo(self, item_id):
        """되돌리기 실행"""
        try:
            if item_id not in self.histories or len(self.histories[item_id]) <= 1:
                return None
            
            self.histories[item_id].pop()
            if self.histories[item_id]:
                prev_state = self.histories[item_id][-1]
                restored_state = [ann.copy() for ann in prev_state]
                
                logger.debug(f"되돌리기 실행 - Item {item_id}: {len(restored_state)}개 주석")
                return restored_state
            
            return []
            
        except Exception as e:
            logger.error(f"되돌리기 오류: {e}")
            return None
    
    def can_undo(self, item_id):
        """되돌리기 가능한지 확인"""
        return (item_id in self.histories and len(self.histories[item_id]) > 1)
    
    def _cleanup_old_histories(self):
        """오래된 히스토리 정리"""
        try:
            empty_keys = [k for k, v in self.histories.items() if not v]
            for k in empty_keys:
                del self.histories[k]
            
            self._last_cleanup = time.time()
            
        except Exception as e:
            logger.debug(f"히스토리 정리 오류: {e}")
    
    def clear_history(self, item_id):
        """특정 항목의 히스토리 초기화"""
        if item_id in self.histories:
            self.histories[item_id].clear()
    
    def clear_all(self):
        """모든 히스토리 초기화"""
        self.histories.clear()

class OptimizedFontManager:
    """최적화된 폰트 관리 클래스"""
    
    def __init__(self):
        self.korean_fonts = []
        self.korean_font_path = None
        self.ui_font = None
        self._font_cache = weakref.WeakValueDictionary()
        self._setup_fonts()
    
    def _setup_fonts(self):
        """시스템 폰트 설정"""
        try:
            font_candidates = [
                ('맑은 고딕', [
                    r'C:\Windows\Fonts\malgun.ttf',
                    r'C:\Windows\Fonts\malgunsl.ttf'
                ]),
                ('Malgun Gothic', [
                    r'C:\Windows\Fonts\malgun.ttf'
                ]),
                ('나눔고딕', [
                    r'C:\Windows\Fonts\NanumGothic.ttf',
                    r'C:\Windows\Fonts\나눔고딕.ttf'
                ]),
                ('Gulim', [r'C:\Windows\Fonts\gulim.ttc']),
                ('Dotum', [r'C:\Windows\Fonts\dotum.ttc']),
                ('Batang', [r'C:\Windows\Fonts\batang.ttc'])
            ]
            
            if sys.platform == 'darwin':
                font_candidates.extend([
                    ('AppleGothic', ['/System/Library/Fonts/AppleGothic.ttf']),
                    ('Helvetica', ['/System/Library/Fonts/Helvetica.ttc'])
                ])
            
            elif sys.platform.startswith('linux'):
                font_candidates.extend([
                    ('Noto Sans CJK KR', [
                        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'
                    ]),
                    ('DejaVu Sans', ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
                ])
            
            selected_font = '맑은 고딕'
            for font_name, paths in font_candidates:
                for path in paths:
                    if os.path.exists(path):
                        selected_font = font_name
                        self.korean_font_path = path
                        logger.info(f"✓ 한글 폰트 발견: {font_name} ({path})")
                        break
                if self.korean_font_path:
                    break
            
            self.ui_font = (selected_font, 10)
            self.ui_font_bold = (selected_font, 10, 'bold')
            self.ui_font_small = (selected_font, 8)
            self.title_font = (selected_font, 12, 'bold')
            self.status_font = (selected_font, 10, 'bold')
            self.text_font = (selected_font, 10)
            # 텍스트 입력용 한글 최적화 설정
            self.text_input_font = (selected_font, 11)
            
            logger.info(f"✓ UI 폰트 설정 완료: {selected_font}")
            
        except Exception as e:
            logger.error(f"폰트 설정 오류: {e}")
            self._setup_fallback_fonts()
    
    def _setup_fallback_fonts(self):
        """기본 폰트 설정"""
        self.ui_font = ('Arial', 10)
        self.ui_font_bold = ('Arial', 10, 'bold')
        self.ui_font_small = ('Arial', 10)
        self.title_font = ('Arial', 12, 'bold')
        self.status_font = ('Arial', 10, 'bold')
        self.text_font = ('Arial', 10)
        self.text_input_font = ('Arial', 11)
    
    def get_pil_font(self, size=12):
        """PIL용 폰트 반환"""
        try:
            cache_key = f"{self.korean_font_path}_{size}"
            
            if cache_key in self._font_cache:
                return self._font_cache[cache_key]
            
            font = None
            if self.korean_font_path and os.path.exists(self.korean_font_path):
                font = ImageFont.truetype(self.korean_font_path, size)
            else:
                font = ImageFont.load_default()
            
            self._font_cache[cache_key] = font
            return font
            
        except Exception as e:
            logger.debug(f"PIL 폰트 로드 실패: {e}")
            return ImageFont.load_default()
    
    def register_pdf_font(self):
        """PDF용 한글 폰트 등록"""
        font_name = 'Helvetica'
        try:
            if self.korean_font_path and os.path.exists(self.korean_font_path):
                pdfmetrics.registerFont(TTFont('Korean', self.korean_font_path))
                font_name = 'Korean'
                logger.info("✓ PDF 한글 폰트 등록 성공")
        except Exception as e:
            logger.warning(f"PDF 한글 폰트 등록 실패: {e}")
        
        return font_name

class AsyncTaskManager:
    """비동기 작업 관리자"""
    
    def __init__(self, root):
        self.root = root
        self.task_queue = queue.Queue()
        self.is_running = True
        self._start_worker()
    
    def _start_worker(self):
        """작업자 스레드 시작"""
        def worker():
            while self.is_running:
                try:
                    task = self.task_queue.get(timeout=1)
                    if task:
                        result = task['func'](*task['args'], **task['kwargs'])
                        if task['callback']:
                            self.root.after(0, lambda: task['callback'](result))
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"비동기 작업 오류: {e}")
                    if task.get('error_callback'):
                        self.root.after(0, lambda: task['error_callback'](e))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def submit_task(self, func, args=(), kwargs={}, callback=None, error_callback=None):
        """작업 제출"""
        task = {
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'callback': callback,
            'error_callback': error_callback
        }
        self.task_queue.put(task)
    
    def shutdown(self):
        """작업 관리자 종료"""
        self.is_running = False

"""
🎯 악어스튜디오 캡쳐 피드백 도구 V1.6.1 - 배포 최적화 버전
==================================================
- 영역 선택으로 다중 주석 선택/이동/삭제
- PDF 텍스트 주석 완벽 출력 (배경/테두리 제거)
- 빈 캔버스 생성 기능 추가
- UI 레이아웃 최적화
- PDF 정보 입력창 분리
- 모든 기능 디버그 및 최적화 완료

🚀 V1.6.1 배포 최적화:
- 동적 디버그 모드 (--debug 플래그 또는 DEBUG_MODE 환경변수)
- 프로덕션 로그 레벨 최적화 (WARNING 이상만 출력)
- 콘솔 창 자동 숨김 (프로덕션 모드)
- 디버그 출력 완전 제거 (프로덕션 모드)
==================================================
"""

import sys
import os
import threading
import time
import json
import io
import base64
import math
import logging
import traceback
import gc
import tempfile
import platform
import shutil
import weakref
from datetime import datetime
from pathlib import Path
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import subprocess

#  PyInstaller one-file 실행 시 리소스 경로 얻기
def resource_path(rel_path: str) -> str:
    base = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base, rel_path)

# 버전 정보
VERSION = "1.6.1"
BUILD_DATE = "2025-01-26"
COPYRIGHT = "Copyright 2025 악어스튜디오 INC. All rights reserved."

# 로깅 설정
def setup_logging():
    """로깅 시스템 설정"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"feedback_tool_{datetime.now().strftime('%Y%m%d')}.log"
    
    try:
        for old_log in log_dir.glob("feedback_tool_*.log"):
            if (datetime.now() - datetime.fromtimestamp(old_log.stat().st_mtime)).days > 7:
                old_log.unlink()
    except Exception:
        pass
    
    # 프로덕션 모드에서는 WARNING 레벨, 디버그 모드에서는 DEBUG 레벨
    is_debug_mode = '--debug' in sys.argv or os.getenv('DEBUG_MODE') == '1'
    log_level = logging.DEBUG if is_debug_mode else logging.WARNING
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler() if is_debug_mode else logging.NullHandler()
        ]
    )
    return logging.getLogger(__name__)

# 🔥 [중복 제거됨] 두 번째 시스템 정보 출력 블록 - 상단으로 통합됨

# 🔥 개선된 화살표 그리기 함수
def create_improved_arrow(canvas, x1, y1, x2, y2, color, width, tags='annotation'):
    """개선된 화살표 그리기 - 선 두께와 길이에 따라 적절한 삼각형 생성"""
    try:
        # 화살표 길이 계산
        arrow_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        # 🔥 동적 화살표 크기 계산
        # 선 두께에 비례하여 화살표 크기 조정
        base_arrow_size = max(8, width * 2.5)  # 최소 8픽셀, 선 두께의 2.5배
        
        # 화살표 길이에 따라 크기 제한
        if arrow_length > 0:
            max_arrow_size = arrow_length * 0.3  # 화살표 길이의 30%까지만
            arrow_size = min(base_arrow_size, max_arrow_size)
        else:
            arrow_size = base_arrow_size
            
        # 🔥 최소 크기 보장 (너무 작으면 삼각형이 안 보임)
        arrow_size = max(arrow_size, 6)
        
        # 화살표가 너무 작은 경우 각도를 더 날카롭게
        if arrow_size < 12:
            angle_offset = math.pi / 8  # 22.5도 (더 날카로운 화살표)
        else:
            angle_offset = math.pi / 6   # 30도 (일반적인 화살표)
        
        # 화살표 방향 계산
        if arrow_length > 0:
            angle = math.atan2(y2 - y1, x2 - x1)
            
            # 🔥 삼각형이 라인보다 앞으로 돌출되도록 계산
            # 삼각형의 기저부 위치 계산 (라인은 여기까지만)
            base_distance = arrow_size * 0.7  # 삼각형 기저부까지의 거리
            base_x = x2 - base_distance * math.cos(angle)
            base_y = y2 - base_distance * math.sin(angle)
            
            # 화살표 라인을 삼각형 기저부까지만 그리기
            canvas.create_line(x1, y1, base_x, base_y, fill=color, width=width, tags=tags)
            
            # 🔥 삼각형 끝점을 더 앞으로 돌출시키기
            extend_distance = arrow_size * 0.15  # 추가 돌출 거리
            tip_x = x2 + extend_distance * math.cos(angle)
            tip_y = y2 + extend_distance * math.sin(angle)
            
            # 화살표 날개 좌표 계산 (원래 끝점 기준)
            wing1_x = x2 - arrow_size * math.cos(angle - angle_offset)
            wing1_y = y2 - arrow_size * math.sin(angle - angle_offset)
            
            wing2_x = x2 - arrow_size * math.cos(angle + angle_offset)
            wing2_y = y2 - arrow_size * math.sin(angle + angle_offset)
            
            # 🔥 뾰족하고 돌출된 삼각형 그리기
            canvas.create_polygon(
                tip_x, tip_y,      # 더 앞으로 돌출된 끝점
                wing1_x, wing1_y,  # 왼쪽 날개
                wing2_x, wing2_y,  # 오른쪽 날개
                fill=color, 
                outline=color,
                width=1,
                tags=tags
            )
            
            logger.debug(f"화살표 생성: 길이={arrow_length:.1f}, 크기={arrow_size:.1f}, 두께={width}")
        
    except Exception as e:
        logger.error(f"개선된 화살표 그리기 오류: {e}")
        # 폴백: 기본 화살표
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_size = 10
        canvas.create_polygon(
            x2 - arrow_size * math.cos(angle - math.pi / 6),
            y2 - arrow_size * math.sin(angle - math.pi / 6),
            x2, y2,
            x2 - arrow_size * math.cos(angle + math.pi / 6),
            y2 - arrow_size * math.sin(angle + math.pi / 6),
            fill=color, tags=tags
        )

# 🔥 [중복 제거됨] 네 번째 V1.6.1 블록 - 상단의 첫 번째 블록으로 통합됨
    
    def update(self, value, detail=""):
        """진행률 업데이트"""
        try:
            if self.canceled:
                return False
                
            self.progress['value'] = min(100, max(0, value))
            self.percent_label.config(text=f"{int(value)}%")
            
            if detail:
                self.detail_label.config(text=detail)
            self.dialog.update()
            return True
        except Exception:
            return False
    
    def cancel(self):
        """취소 처리"""
        self.canceled = True
        if self.cancel_callback:
            self.cancel_callback()
        self.close()
    
    def set_cancel_callback(self, callback):
        """취소 콜백 설정"""
        self.cancel_callback = callback
    
    def close(self):
        """다이얼로그 닫기"""
        try:
            self.dialog.destroy()
        except Exception:
            pass

class SmartUndoManager:
    """스마트 되돌리기 관리 클래스"""
    
    def __init__(self, max_history=8):
        self.max_history = max_history
        self.histories = {}
        self._last_cleanup = time.time()
    
    def save_state(self, item_id, annotations):
        """현재 주석 상태 저장"""
        try:
            if item_id not in self.histories:
                self.histories[item_id] = deque(maxlen=self.max_history)
            
            state = [ann.copy() for ann in annotations]
            self.histories[item_id].append(state)
            
            if time.time() - self._last_cleanup > 300:
                self._cleanup_old_histories()
                
            logger.debug(f"상태 저장됨 - Item {item_id}: {len(state)}개 주석")
            
        except Exception as e:
            logger.error(f"상태 저장 오류: {e}")
    
    def undo(self, item_id):
        """되돌리기 실행"""
        try:
            if item_id not in self.histories or len(self.histories[item_id]) <= 1:
                return None
            
            self.histories[item_id].pop()
            if self.histories[item_id]:
                prev_state = self.histories[item_id][-1]
                restored_state = [ann.copy() for ann in prev_state]
                
                logger.debug(f"되돌리기 실행 - Item {item_id}: {len(restored_state)}개 주석")
                return restored_state
            
            return []
            
        except Exception as e:
            logger.error(f"되돌리기 오류: {e}")
            return None
    
    def can_undo(self, item_id):
        """되돌리기 가능한지 확인"""
        return (item_id in self.histories and len(self.histories[item_id]) > 1)
    
    def _cleanup_old_histories(self):
        """오래된 히스토리 정리"""
        try:
            empty_keys = [k for k, v in self.histories.items() if not v]
            for k in empty_keys:
                del self.histories[k]
            
            self._last_cleanup = time.time()
            
        except Exception as e:
            logger.debug(f"히스토리 정리 오류: {e}")
    
    def clear_history(self, item_id):
        """특정 항목의 히스토리 초기화"""
        if item_id in self.histories:
            self.histories[item_id].clear()
    
    def clear_all(self):
        """모든 히스토리 초기화"""
        self.histories.clear()

class OptimizedFontManager:
    """최적화된 폰트 관리 클래스"""
    
    def __init__(self):
        self.korean_fonts = []
        self.korean_font_path = None
        self.ui_font = None
        self._font_cache = weakref.WeakValueDictionary()
        self._setup_fonts()
    
    def _setup_fonts(self):
        """시스템 폰트 설정"""
        try:
            font_candidates = [
                ('맑은 고딕', [
                    r'C:\Windows\Fonts\malgun.ttf',
                    r'C:\Windows\Fonts\malgunsl.ttf'
                ]),
                ('Malgun Gothic', [
                    r'C:\Windows\Fonts\malgun.ttf'
                ]),
                ('나눔고딕', [
                    r'C:\Windows\Fonts\NanumGothic.ttf',
                    r'C:\Windows\Fonts\나눔고딕.ttf'
                ]),
                ('Gulim', [r'C:\Windows\Fonts\gulim.ttc']),
                ('Dotum', [r'C:\Windows\Fonts\dotum.ttc']),
                ('Batang', [r'C:\Windows\Fonts\batang.ttc'])
            ]
            
            if sys.platform == 'darwin':
                font_candidates.extend([
                    ('AppleGothic', ['/System/Library/Fonts/AppleGothic.ttf']),
                    ('Helvetica', ['/System/Library/Fonts/Helvetica.ttc'])
                ])
            
            elif sys.platform.startswith('linux'):
                font_candidates.extend([
                    ('Noto Sans CJK KR', [
                        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'
                    ]),
                    ('DejaVu Sans', ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
                ])
            
            selected_font = '맑은 고딕'
            for font_name, paths in font_candidates:
                for path in paths:
                    if os.path.exists(path):
                        selected_font = font_name
                        self.korean_font_path = path
                        logger.info(f"✓ 한글 폰트 발견: {font_name} ({path})")
                        break
                if self.korean_font_path:
                    break
            
            self.ui_font = (selected_font, 10)
            self.ui_font_bold = (selected_font, 10, 'bold')
            self.ui_font_small = (selected_font, 9)
            self.title_font = (selected_font, 12, 'bold')
            self.status_font = (selected_font, 10, 'bold')
            self.text_font = (selected_font, 10)
            # 텍스트 입력용 한글 최적화 설정
            self.text_input_font = (selected_font, 11)
            
            logger.info(f"✓ UI 폰트 설정 완료: {selected_font}")
            
        except Exception as e:
            logger.error(f"폰트 설정 오류: {e}")
            self._setup_fallback_fonts()
    
    def _setup_fallback_fonts(self):
        """기본 폰트 설정"""
        self.ui_font = ('Arial', 10)
        self.ui_font_bold = ('Arial', 10, 'bold')
        self.ui_font_small = ('Arial', 9)
        self.title_font = ('Arial', 12, 'bold')
        self.status_font = ('Arial', 10, 'bold')
        self.text_font = ('Arial', 10)
        self.text_input_font = ('Arial', 11)
    
    def get_pil_font(self, size=12):
        """PIL용 폰트 반환"""
        try:
            cache_key = f"{self.korean_font_path}_{size}"
            
            if cache_key in self._font_cache:
                return self._font_cache[cache_key]
            
            font = None
            if self.korean_font_path and os.path.exists(self.korean_font_path):
                font = ImageFont.truetype(self.korean_font_path, size)
            else:
                font = ImageFont.load_default()
            
            self._font_cache[cache_key] = font
            return font
            
        except Exception as e:
            logger.debug(f"PIL 폰트 로드 실패: {e}")
            return ImageFont.load_default()
    
    def register_pdf_font(self):
        """PDF용 한글 폰트 등록"""
        font_name = 'Helvetica'
        try:
            if self.korean_font_path and os.path.exists(self.korean_font_path):
                pdfmetrics.registerFont(TTFont('Korean', self.korean_font_path))
                font_name = 'Korean'
                logger.info("✓ PDF 한글 폰트 등록 성공")
        except Exception as e:
            logger.warning(f"PDF 한글 폰트 등록 실패: {e}")
        
        return font_name

class AsyncTaskManager:
    """비동기 작업 관리자"""
    
    def __init__(self, root):
        self.root = root
        self.task_queue = queue.Queue()
        self.is_running = True
        self._start_worker()
    
    def _start_worker(self):
        """작업자 스레드 시작"""
        def worker():
            while self.is_running:
                try:
                    task = self.task_queue.get(timeout=1)
                    if task:
                        result = task['func'](*task['args'], **task['kwargs'])
                        if task['callback']:
                            self.root.after(0, lambda: task['callback'](result))
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"비동기 작업 오류: {e}")
                    if task.get('error_callback'):
                        self.root.after(0, lambda: task['error_callback'](e))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def submit_task(self, func, args=(), kwargs={}, callback=None, error_callback=None):
        """작업 제출"""
        task = {
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'callback': callback,
            'error_callback': error_callback
        }
        self.task_queue.put(task)
    
    def shutdown(self):
        """작업 관리자 종료"""
        self.is_running = False

class HighQualityPDFGenerator:
    """고화질 PDF 생성기"""
    
    def __init__(self, font_manager, app_instance=None):
        self.font_manager = font_manager
        self.app = app_instance
        self.target_dpi = 300
        self.vector_annotations = True
        self.dragging_text = None
        self.drag_start_x = None
        self.drag_start_y = None
        self.original_text_x = None
        self.original_text_y = None
        # PDF 가독성 모드 옵션 (다이얼로그에서 전달받음)
        self.pdf_readability_mode = False  # 기본값은 항상 False, 명시적으로 설정해야만 True
        
    def set_readability_mode(self, enabled):
        """PDF 가독성 모드 설정"""
        self.pdf_readability_mode = enabled
        
    def create_high_quality_combined_image(self, item, target_width=None, target_height=None):
        """최고 화질의 합성 이미지 생성 (투명도 완벽 지원)"""
        try:
            original_image = item['image'].copy()
            annotations = item.get('annotations', [])
            logger.debug(f"합성 이미지 생성 시작: 기본 크기 {original_image.width}x{original_image.height}, 주석 {len(annotations)}개")
            
            if target_width and target_height:
                original_ratio = original_image.width / original_image.height
                target_ratio = target_width / target_height
                
                if original_ratio > target_ratio:
                    new_width = target_width
                    new_height = int(target_width / original_ratio)
                else:
                    new_height = target_height
                    new_width = int(target_height * original_ratio)
                
                if new_width != original_image.width or new_height != original_image.height:
                    logger.debug(f"이미지 크기 조정: {original_image.width}x{original_image.height} -> {new_width}x{new_height}")
                    original_image = original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 🔥 투명도가 있는 이미지 주석 확인
            image_annotations = [ann for ann in annotations if ann.get('type') == 'image']
            has_transparent_images = any(
                ann.get('opacity', 100) < 100 
                for ann in image_annotations
            )
            
            logger.info(f"🎨 이미지 주석 분석: 총 {len(image_annotations)}개, 투명도 있음: {has_transparent_images}")
            
            if has_transparent_images:
                # 🔥 투명도가 있는 경우 RGBA 모드 유지
                logger.info("🎨 투명도 감지: RGBA 모드로 처리")
                
                if original_image.mode != 'RGBA':
                    original_image = original_image.convert('RGBA')
                
                # RGBA 모드에서 투명도 지원하는 주석 그리기
                draw = ImageDraw.Draw(original_image)
                
                for i, annotation in enumerate(annotations):
                    try:
                        if annotation.get('type') == 'image':
                            # 투명도 지원 이미지 주석 그리기
                            self._draw_transparent_image_annotation(original_image, annotation)
                            logger.debug(f"투명도 이미지 주석 {i+1} 완료")
                        else:
                            # 다른 주석들은 기존 방식
                            self._draw_high_quality_annotation(draw, annotation, original_image.size)
                    except Exception as e:
                        logger.error(f"주석 {i+1} 그리기 오류: {e}")
                        continue
                
                logger.info(f"🎨 투명도 지원 합성 완료: {original_image.mode}, 크기: {original_image.width}x{original_image.height}")
                return original_image
            
            else:
                # 🔥 투명도가 없는 경우만 RGB 변환
                logger.info("🎨 투명도 없음: RGB 모드로 처리")
                
                if original_image.mode != 'RGB':
                    rgb_image = Image.new('RGB', original_image.size, (255, 255, 255))
                    if 'A' in original_image.mode:
                        rgb_image.paste(original_image, mask=original_image.split()[-1])
                    else:
                        rgb_image.paste(original_image)
                    original_image = rgb_image
                    logger.debug(f"RGB 변환 완료: {original_image.mode}")
                
                draw = ImageDraw.Draw(original_image)
                
                # 주석 그리기
                for i, annotation in enumerate(annotations):
                    try:
                        self._draw_high_quality_annotation(draw, annotation, original_image.size)
                    except Exception as e:
                        logger.error(f"주석 {i+1} 그리기 오류: {e}")
                        continue
                
                logger.debug(f"최종 합성 이미지: {original_image.width}x{original_image.height}, 모드: {original_image.mode}")
                return original_image
                
        except Exception as e:
            logger.error(f"고화질 이미지 생성 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return item['image']
    
    def _draw_high_quality_annotation(self, draw, annotation, image_size):
        """고화질 주석 그리기"""
        try:
            ann_type = annotation['type']
            color = annotation.get('color', '#ff0000')
            # 🔥 고화질 이미지에서 선 두께 조정 - 원본에 더 가깝게
            base_width = annotation.get('width', 2)
            width = max(2, int(base_width * 1.3))  # 기존 2배에서 1.3배로 조정
            
            if ann_type == 'arrow':
                x1, y1 = annotation['start_x'], annotation['start_y']
                x2, y2 = annotation['end_x'], annotation['end_y']
                

                
                # 🔥 PDF용 개선된 화살표 그리기
                if abs(x2 - x1) > 1 or abs(y2 - y1) > 1:
                    angle = math.atan2(y2 - y1, x2 - x1)
                    
                    # 동적 화살표 크기 계산
                    arrow_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                    base_arrow_size = max(20, width * 3)
                    max_arrow_size = arrow_length * 0.3
                    arrow_size = min(base_arrow_size, max_arrow_size)
                    arrow_size = max(arrow_size, 15)  # PDF에서는 최소 크기를 조금 더 크게
                    
                    # 작은 화살표는 더 날카롭게
                    angle_offset = math.pi / 8 if arrow_size < 30 else math.pi / 6
                    
                    # 삼각형이 라인보다 앞으로 돌출되도록 계산
                    base_distance = arrow_size * 0.7
                    base_x = x2 - base_distance * math.cos(angle)
                    base_y = y2 - base_distance * math.sin(angle)
                    
                    # 가독성 모드: 흰색 아웃라인 먼저 그리기
                    if self.pdf_readability_mode:
                        # 흰색 아웃라인 라인
                        draw.line([(x1, y1), (base_x, base_y)], fill='white', width=width+2)
                        
                        # 삼각형 끝점을 더 앞으로 돌출시키기
                        extend_distance = arrow_size * 0.15
                        tip_x = x2 + extend_distance * math.cos(angle)
                        tip_y = y2 + extend_distance * math.sin(angle)
                        
                        # 화살표 날개 좌표 계산
                        wing1_x = x2 - arrow_size * math.cos(angle - angle_offset)
                        wing1_y = y2 - arrow_size * math.sin(angle - angle_offset)
                        wing2_x = x2 - arrow_size * math.cos(angle + angle_offset)
                        wing2_y = y2 - arrow_size * math.sin(angle + angle_offset)
                        
                        # 흰색 아웃라인 삼각형
                        arrow_points = [(tip_x, tip_y), (wing1_x, wing1_y), (wing2_x, wing2_y)]
                        draw.polygon(arrow_points, fill='white', outline='white')
                    
                    # 화살표 라인을 삼각형 기저부까지만 그리기
                    draw.line([(x1, y1), (base_x, base_y)], fill=color, width=width)
                    
                    # 삼각형 끝점을 더 앞으로 돌출시키기
                    extend_distance = arrow_size * 0.15
                    tip_x = x2 + extend_distance * math.cos(angle)
                    tip_y = y2 + extend_distance * math.sin(angle)
                    
                    # 화살표 날개 좌표 계산
                    wing1_x = x2 - arrow_size * math.cos(angle - angle_offset)
                    wing1_y = y2 - arrow_size * math.sin(angle - angle_offset)
                    wing2_x = x2 - arrow_size * math.cos(angle + angle_offset)
                    wing2_y = y2 - arrow_size * math.sin(angle + angle_offset)
                    
                    # 뾰족하고 돌출된 삼각형 그리기
                    arrow_points = [(tip_x, tip_y), (wing1_x, wing1_y), (wing2_x, wing2_y)]
                    draw.polygon(arrow_points, fill=color, outline=color)
                else:
                    # 화살표가 너무 작은 경우 단순 라인
                    if self.pdf_readability_mode:
                        draw.line([(x1, y1), (x2, y2)], fill='white', width=width+2)
                    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
            
            elif ann_type == 'line':
                # 라인 그리기 (화살표 머리 없는 단순한 선)
                x1, y1 = annotation['start_x'], annotation['start_y']
                x2, y2 = annotation['end_x'], annotation['end_y']
                
                # 가독성 모드: 흰색 아웃라인
                if self.pdf_readability_mode:
                    draw.line([(x1, y1), (x2, y2)], fill='white', width=width+2)
                
                draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
            
            elif ann_type == 'pen':
                points = annotation.get('points', [])
                if len(points) > 1:
                    smoothed_points = self._smooth_path(points)
                    
                    # 가독성 모드: 흰색 아웃라인
                    if self.pdf_readability_mode:
                        for i in range(len(smoothed_points) - 1):
                            draw.line([smoothed_points[i], smoothed_points[i+1]], 
                                    fill='white', width=width+2)
                    
                    # 원래 색상으로 그리기
                    for i in range(len(smoothed_points) - 1):
                        draw.line([smoothed_points[i], smoothed_points[i+1]], 
                                fill=color, width=width)
            
            elif ann_type == 'oval':
                x1, y1 = annotation['x1'], annotation['y1']
                x2, y2 = annotation['x2'], annotation['y2']
                
                # 가독성 모드: 흰색 아웃라인
                if self.pdf_readability_mode:
                    draw.ellipse([min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)], 
                               outline='white', width=width+2)
                
                draw.ellipse([min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)], 
                           outline=color, width=width)
            
            elif ann_type == 'rect':
                x1, y1 = annotation['x1'], annotation['y1']
                x2, y2 = annotation['x2'], annotation['y2']
                
                # 가독성 모드: 흰색 아웃라인
                if self.pdf_readability_mode:
                    draw.rectangle([min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)], 
                                 outline='white', width=width+2)
                
                draw.rectangle([min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)], 
                             outline=color, width=width)
            
            elif ann_type == 'text':
                x, y = annotation['x'], annotation['y']
                text = annotation.get('text', '')
                base_font_size = annotation.get('font_size', 12)
                
                # 🔥 원본 크기와 동일하게 폰트 크기 유지 (2배 과대화 제거)
                font_size = max(base_font_size, 10)  # 최소 10px 보장
                font = self.font_manager.get_pil_font(font_size)
                
                # 가독성 모드: 텍스트 배경 추가 (글자 크기에 비례한 적절한 여백)
                if self.pdf_readability_mode and text.strip():
                    # 텍스트 크기 측정
                    bbox = draw.textbbox((x, y), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    
                    # 폰트 크기에 비례한 적절한 여백 (폰트 크기의 약 15%)
                    padding = max(3, font_size * 0.15)
                    bg_x1 = x - padding
                    bg_y1 = y - padding
                    bg_x2 = x + text_width + padding
                    bg_y2 = y + text_height + padding
                    
                    # 흰색 배경 그리기 (불투명하게)
                    draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], 
                                 fill='white', outline='#d0d0d0')
                
                # 텍스트 그리기
                draw.text((x, y), text, fill=color, font=font)
            
            elif ann_type == 'image':
                # 🔥 중요: 이미지 주석은 여기서 처리하지 않음!
                # _draw_transparent_image_annotation 메서드에서 별도 처리
                logger.debug("이미지 주석은 투명도 전용 메서드에서 처리됨")
                return
        
        except Exception as e:
            logger.debug(f"개별 주석 그리기 오류: {e}")
    
    def _smooth_path(self, points):
        """펜 경로 스무딩"""
        if len(points) <= 2:
            return points
        
        smoothed = [points[0]]
        
        for i in range(1, len(points) - 1):
            prev_point = points[i - 1]
            curr_point = points[i]
            next_point = points[i + 1]
            
            smooth_x = (prev_point[0] + curr_point[0] + next_point[0]) / 3
            smooth_y = (prev_point[1] + curr_point[1] + next_point[1]) / 3
            
            smoothed.append((smooth_x, smooth_y))
        
        smoothed.append(points[-1])
        return smoothed
    
    def create_vector_pdf_page(self, canvas, item, index, page_width, page_height):
        """벡터 기반 PDF 페이지 생성 - 하단 여백 축소"""
        try:
            margin = 50
            usable_width = page_width - (margin * 2)
            
            feedback_text = item.get('feedback_text', '').strip()
            text_area_height = 0
            bottom_margin = 25  # 🔥 하단 여백 대폭 축소 (기존 60 → 25)
            
            if feedback_text:
                korean_font = self.font_manager.register_pdf_font()
                temp_canvas = pdf_canvas.Canvas("temp.pdf", pagesize=A4)
                max_text_width = usable_width - 40
                text_lines = self._wrap_text_for_pdf(feedback_text, max_text_width, korean_font, 11, temp_canvas)
                
                line_height = 18
                title_space = 30  # 제목 공간 대폭 축소 (60 → 30)
                text_area_height = max(60, len(text_lines) * line_height + title_space + 20)  # 최소값 절반 축소 (120 → 60), 여백 절반 축소 (40 → 20)
                
                max_text_height = page_height * 0.4
                if text_area_height > max_text_height:
                    text_area_height = max_text_height
            
            image_text_gap = 25
            usable_height = page_height - (margin * 2) - bottom_margin - text_area_height - image_text_gap
            
            img = item['image']
            img_ratio = img.width / img.height
            
            if img.width > usable_width or img.height > usable_height:
                if img_ratio > (usable_width / usable_height):
                    new_width = usable_width
                    new_height = usable_width / img_ratio
                else:
                    new_height = usable_height
                    new_width = usable_height * img_ratio
            else:
                new_width = img.width
                new_height = img.height
            
            img_x = (page_width - new_width) / 2
            img_y = page_height - margin - new_height - 10
            
            clean_image = self.create_clean_image_for_pdf(item)
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                high_res_width = int(new_width * 2)
                high_res_height = int(new_height * 2)
                
                if high_res_width != clean_image.width or high_res_height != clean_image.height:
                    clean_image = clean_image.resize((high_res_width, high_res_height), Image.Resampling.LANCZOS)
                
                clean_image.save(tmp_file.name, format='PNG', optimize=False, compress_level=0)
                
                canvas.drawImage(tmp_file.name, img_x, img_y, new_width, new_height, preserveAspectRatio=True)
                
                try:
                    os.unlink(tmp_file.name)
                except:
                    pass
            
            self.draw_vector_annotations_on_pdf(canvas, item, img_x, img_y, new_width, new_height)
            
            if feedback_text:
                text_start_y = img_y - image_text_gap
                self._add_feedback_text_to_pdf(canvas, item, index, text_start_y, text_area_height, page_width, margin)
            
            # 꼬리말 추가 (첫 장만 출력 옵션 지원)
            if self.app and hasattr(self.app, 'project_footer') and self.app.project_footer.get():
                # 첫 장만 출력 설정 확인
                show_footer = True
                if hasattr(self.app, 'footer_first_page_only') and self.app.footer_first_page_only.get():
                    # 🔥 제목 페이지가 있을 때는 피드백 페이지에서 꼬리말 출력하지 않음
                    skip_title = getattr(self.app, 'skip_title_page', False)
                    if skip_title:
                        show_footer = (index == 0)  # 제목 페이지가 없으면 첫 번째 피드백 페이지에만 표시
                    else:
                        show_footer = False  # 제목 페이지가 있으면 피드백 페이지에서는 꼬리말 출력하지 않음
                
                if show_footer:
                    korean_font = self.font_manager.register_pdf_font()
                    canvas.setFont(korean_font, 10)
                    footer_text = self.app.project_footer.get().strip()
                    footer_width = canvas.stringWidth(footer_text, korean_font, 10)
                    canvas.drawString((page_width - footer_width) / 2, 15, footer_text)  # 꼬리말 더 아래로 (25 → 15)
            
            # 🔥 페이지 번호 계산 (첫장 제외 시 조정)
            skip_title = getattr(self.app, 'skip_title_page', False)
            page_number = index + 1 if skip_title else index + 2
            
            canvas.setFont('Helvetica', 10)
            canvas.drawString(page_width - 80, 15, f"- {page_number} -")  # 페이지 번호 더 아래로 (25 → 15)
            
        except Exception as e:
            logger.error(f"벡터 PDF 페이지 생성 오류: {e}")
            self._fallback_pdf_page(canvas, item, index, page_width, page_height)

    def create_clean_image_for_pdf(self, item):
        """PDF용 깨끗한 이미지 생성 (주석 제외)"""
        try:
            clean_image = item['image'].copy()
            
            if clean_image.mode != 'RGB':
                rgb_image = Image.new('RGB', clean_image.size, (255, 255, 255))
                if 'A' in clean_image.mode:
                    rgb_image.paste(clean_image, mask=clean_image.split()[-1])
                else:
                    rgb_image.paste(clean_image)
                clean_image = rgb_image
            
            return clean_image
            
        except Exception as e:
            logger.error(f"깨끗한 이미지 생성 오류: {e}")
            return item['image']

    def draw_vector_annotations_on_pdf(self, canvas, item, img_x, img_y, img_width, img_height):
        """PDF에 벡터 기반 주석 그리기 (개선된 텍스트 처리)"""
        try:
            if not item.get('annotations'):
                return
            
            scale_x = img_width / item['image'].width
            scale_y = img_height / item['image'].height
            
            for annotation in item['annotations']:
                try:
                    ann_type = annotation['type']
                    color_hex = annotation.get('color', '#ff0000')
                    
                    if color_hex.startswith('#'):
                        color_hex = color_hex[1:]
                    r = int(color_hex[0:2], 16) / 255.0
                    g = int(color_hex[2:4], 16) / 255.0
                    b = int(color_hex[4:6], 16) / 255.0
                    
                    canvas.setStrokeColorRGB(r, g, b)
                    canvas.setFillColorRGB(r, g, b)
                    
                    # 🔥 선 두께 스케일링 조정 - 원본에 더 가깝게
                    base_width = annotation.get('width', 2)
                    # 스케일 팩터를 줄여서 원본 크기에 더 가깝게 유지
                    scale_factor = min(scale_x, scale_y) * 0.7  # 기존 스케일의 70%로 조정
                    line_width = max(1.0, base_width * scale_factor)  # 최소 두께 증가
                    canvas.setLineWidth(line_width)
                    
                    if ann_type == 'arrow':
                        x1 = img_x + annotation['start_x'] * scale_x
                        y1 = img_y + (item['image'].height - annotation['start_y']) * scale_y
                        x2 = img_x + annotation['end_x'] * scale_x
                        y2 = img_y + (item['image'].height - annotation['end_y']) * scale_y
                        
                        # 가독성 모드: 흰색 아웃라인
                        if self.pdf_readability_mode:
                            canvas.setStrokeColorRGB(1, 1, 1)  # 흰색
                            canvas.setLineWidth(line_width + 2)
                        
                        # 🔥 PDF ReportLab용 개선된 화살표 그리기 (좌표계 수정)
                        if abs(x2 - x1) > 1 or abs(y2 - y1) > 1:
                            # PDF 좌표계에 맞는 올바른 각도 계산
                            angle = math.atan2(y2 - y1, x2 - x1)
                            
                            # 동적 화살표 크기 계산
                            arrow_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                            base_arrow_size = max(10, line_width * 3)
                            max_arrow_size = arrow_length * 0.3
                            arrow_size = min(base_arrow_size, max_arrow_size)
                            arrow_size = max(arrow_size, 8)  # PDF에서 최소 크기
                            
                            # 작은 화살표는 더 날카롭게
                            angle_offset = math.pi / 8 if arrow_size < 20 else math.pi / 6
                            
                            # 삼각형이 라인보다 앞으로 돌출되도록 계산
                            base_distance = arrow_size * 0.7
                            base_x = x2 - base_distance * math.cos(angle)
                            base_y = y2 - base_distance * math.sin(angle)
                            
                            # 화살표 라인을 삼각형 기저부까지만 그리기
                            canvas.line(x1, y1, base_x, base_y)
                            
                            # 삼각형 끝점을 더 앞으로 돌출시키기
                            extend_distance = arrow_size * 0.15
                            tip_x = x2 + extend_distance * math.cos(angle)
                            tip_y = y2 + extend_distance * math.sin(angle)
                            
                            # 화살표 날개 좌표 계산
                            wing1_x = x2 - arrow_size * math.cos(angle - angle_offset)
                            wing1_y = y2 - arrow_size * math.sin(angle - angle_offset)
                            wing2_x = x2 - arrow_size * math.cos(angle + angle_offset)
                            wing2_y = y2 - arrow_size * math.sin(angle + angle_offset)
                            
                            # 뾰족하고 돌출된 삼각형 그리기 (흰색 아웃라인)
                            if self.pdf_readability_mode:
                                path = canvas.beginPath()
                                path.moveTo(tip_x, tip_y)
                                path.lineTo(wing1_x, wing1_y)
                                path.lineTo(wing2_x, wing2_y)
                                path.close()
                                canvas.drawPath(path, fill=1, stroke=1)
                                canvas.line(x1, y1, base_x, base_y)
                                
                                # 원래 색상으로 다시 설정
                                canvas.setStrokeColorRGB(r, g, b)
                                canvas.setFillColorRGB(r, g, b)
                                canvas.setLineWidth(line_width)
                            
                            # 화살표 라인을 삼각형 기저부까지만 그리기
                            canvas.line(x1, y1, base_x, base_y)
                            
                            # 뾰족하고 돌출된 삼각형 그리기
                            path = canvas.beginPath()
                            path.moveTo(tip_x, tip_y)
                            path.lineTo(wing1_x, wing1_y)
                            path.lineTo(wing2_x, wing2_y)
                            path.close()
                            canvas.drawPath(path, fill=1, stroke=1)
                        else:
                            # 화살표가 너무 작은 경우 단순 라인
                            if self.pdf_readability_mode:
                                canvas.line(x1, y1, x2, y2)
                                # 원래 색상으로 다시 설정
                                canvas.setStrokeColorRGB(r, g, b)
                                canvas.setLineWidth(line_width)
                            canvas.line(x1, y1, x2, y2)
                    
                    elif ann_type == 'line':
                        # 라인 그리기 (화살표 머리 없는 단순한 선)
                        x1 = img_x + annotation['start_x'] * scale_x
                        y1 = img_y + (item['image'].height - annotation['start_y']) * scale_y
                        x2 = img_x + annotation['end_x'] * scale_x
                        y2 = img_y + (item['image'].height - annotation['end_y']) * scale_y
                        
                        # 가독성 모드: 흰색 아웃라인
                        if self.pdf_readability_mode:
                            canvas.setStrokeColorRGB(1, 1, 1)  # 흰색
                            canvas.setLineWidth(line_width + 2)
                            canvas.line(x1, y1, x2, y2)
                            # 원래 색상으로 다시 설정
                            canvas.setStrokeColorRGB(r, g, b)
                            canvas.setLineWidth(line_width)
                        
                        canvas.line(x1, y1, x2, y2)
                    
                    elif ann_type == 'pen':
                        points = annotation.get('points', [])
                        if len(points) > 1:
                            # 가독성 모드: 흰색 아웃라인
                            if self.pdf_readability_mode:
                                canvas.setStrokeColorRGB(1, 1, 1)  # 흰색
                                canvas.setLineWidth(line_width + 2)
                                for i in range(len(points) - 1):
                                    x1 = img_x + points[i][0] * scale_x
                                    y1 = img_y + (item['image'].height - points[i][1]) * scale_y
                                    x2 = img_x + points[i+1][0] * scale_x
                                    y2 = img_y + (item['image'].height - points[i+1][1]) * scale_y
                                    canvas.line(x1, y1, x2, y2)
                                # 원래 색상으로 다시 설정
                                canvas.setStrokeColorRGB(r, g, b)
                                canvas.setLineWidth(line_width)
                            
                            # 원래 색상으로 그리기
                            for i in range(len(points) - 1):
                                x1 = img_x + points[i][0] * scale_x
                                y1 = img_y + (item['image'].height - points[i][1]) * scale_y
                                x2 = img_x + points[i+1][0] * scale_x
                                y2 = img_y + (item['image'].height - points[i+1][1]) * scale_y
                                canvas.line(x1, y1, x2, y2)
                    
                    elif ann_type == 'oval':
                        x1 = img_x + annotation['x1'] * scale_x
                        y1 = img_y + (item['image'].height - annotation['y1']) * scale_y
                        x2 = img_x + annotation['x2'] * scale_x
                        y2 = img_y + (item['image'].height - annotation['y2']) * scale_y
                        
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2
                        width = abs(x2 - x1)
                        height = abs(y2 - y1)
                        
                        # 가독성 모드: 흰색 아웃라인
                        if self.pdf_readability_mode:
                            canvas.setStrokeColorRGB(1, 1, 1)  # 흰색
                            canvas.setLineWidth(line_width + 2)
                            canvas.ellipse(center_x - width/2, center_y - height/2,
                                         center_x + width/2, center_y + height/2,
                                         stroke=1, fill=0)
                            # 원래 색상으로 다시 설정
                            canvas.setStrokeColorRGB(r, g, b)
                            canvas.setLineWidth(line_width)
                        
                        canvas.ellipse(center_x - width/2, center_y - height/2,
                                     center_x + width/2, center_y + height/2,
                                     stroke=1, fill=0)
                    
                    elif ann_type == 'rect':
                        x1 = img_x + annotation['x1'] * scale_x
                        y1 = img_y + (item['image'].height - annotation['y1']) * scale_y
                        x2 = img_x + annotation['x2'] * scale_x
                        y2 = img_y + (item['image'].height - annotation['y2']) * scale_y
                        
                        # 가독성 모드: 흰색 아웃라인
                        if self.pdf_readability_mode:
                            canvas.setStrokeColorRGB(1, 1, 1)  # 흰색
                            canvas.setLineWidth(line_width + 2)
                            canvas.rect(min(x1, x2), min(y1, y2),
                                       abs(x2 - x1), abs(y2 - y1),
                                       stroke=1, fill=0)
                            # 원래 색상으로 다시 설정
                            canvas.setStrokeColorRGB(r, g, b)
                            canvas.setLineWidth(line_width)
                        
                        canvas.rect(min(x1, x2), min(y1, y2),
                                   abs(x2 - x1), abs(y2 - y1),
                                   stroke=1, fill=0)
                    
                    elif ann_type == 'text':
                        # 🔥 텍스트 주석 좌표와 크기 정확히 맞추기
                        x = img_x + annotation['x'] * scale_x
                        # PDF 좌표계에서 y축은 하단부터 시작하므로 올바른 계산
                        y = img_y + (item['image'].height - annotation['y']) * scale_y
                        text = annotation.get('text', '')
                        
                        # 🔥 PDF에서 텍스트 크기를 이미지 스케일에 맞춰 조정
                        base_font_size = annotation.get('font_size', 12)
                        # 이미지 스케일링에 맞춰 텍스트 크기도 조정 (약간 확대)
                        scale_factor = min(scale_x, scale_y)  # 작은 스케일 사용하여 비율 유지
                        pdf_font_size = max(10, int(base_font_size * scale_factor * 1.15))  # 15% 확대, 최소 10px 보장
                        
                        # 🔥 볼드 텍스트 지원 추가
                        is_bold = annotation.get('bold', False)
                        korean_font = self.font_manager.register_pdf_font()
                        canvas.setFont(korean_font, pdf_font_size)
                        
                        # 가독성 모드: 텍스트 배경 추가
                        if self.pdf_readability_mode and text.strip():
                            text_width = canvas.stringWidth(text, korean_font, pdf_font_size)
                            padding = max(3, pdf_font_size * 0.15)
                            
                            # 흰색 배경 사각형
                            canvas.setFillColorRGB(1, 1, 1)  # 흰색
                            canvas.setStrokeColorRGB(0.8, 0.8, 0.8)  # 회색 테두리
                            canvas.setLineWidth(0.5)
                            canvas.rect(x - padding, y - pdf_font_size - padding,
                                       text_width + padding * 2, pdf_font_size + padding * 2,
                                       stroke=1, fill=1)
                        
                        # 텍스트 그리기 - 위치 보정 및 볼드 처리
                        canvas.setFillColorRGB(r, g, b)
                        
                        if is_bold:
                            # 볼드 효과: 텍스트를 더 두껍게 여러 번 그리기
                            base_y = y - pdf_font_size
                            # 볼드 효과를 위한 다중 그리기 (더 두껍게)
                            offsets = [
                                (0, 0), (0.5, 0), (0, 0.5), (0.5, 0.5),  # 기본 4방향
                                (0.25, 0), (0, 0.25), (0.25, 0.25),      # 추가 3방향
                                (0.75, 0), (0, 0.75)                     # 더 두꺼운 효과
                            ]
                            for dx, dy in offsets:
                                canvas.drawString(x + dx, base_y + dy, text)
                        else:
                            canvas.drawString(x, y - pdf_font_size, text)
                    
                    elif ann_type == 'image':
                        try:
                            # 이미지 주석 좌표 계산 (PDF 좌표계 고려)
                            x = img_x + annotation['x'] * scale_x
                            y = img_y + (item['image'].height - annotation['y']) * scale_y
                            width = annotation['width'] * scale_x
                            height = annotation['height'] * scale_y
                            
                            # base64 이미지 디코딩
                            image_data = base64.b64decode(annotation['image_data'])
                            img = Image.open(io.BytesIO(image_data))
                            
                            # 🔥 고해상도 처리를 위한 DPI 스케일링 계산
                            # PDF는 300 DPI가 표준이므로 고품질을 위해 2-3배 크기로 처리
                            quality_multiplier = 2.5  # 품질 향상을 위한 배율
                            high_res_width = max(int(width * quality_multiplier), int(annotation['width'] * quality_multiplier))
                            high_res_height = max(int(height * quality_multiplier), int(annotation['height'] * quality_multiplier))
                            
                            # 원본 이미지가 작을 경우 최소 크기 보장
                            min_size = 200  # 최소 픽셀 크기
                            if high_res_width < min_size or high_res_height < min_size:
                                aspect_ratio = img.width / img.height
                                if high_res_width < min_size:
                                    high_res_width = min_size
                                    high_res_height = int(min_size / aspect_ratio)
                                if high_res_height < min_size:
                                    high_res_height = min_size
                                    high_res_width = int(min_size * aspect_ratio)
                            
                            # 변형 적용 (고해상도로 처리하기 전에)
                            if annotation.get('flip_horizontal', False):
                                img = img.transpose(Image.FLIP_LEFT_RIGHT)
                            if annotation.get('flip_vertical', False):
                                img = img.transpose(Image.FLIP_TOP_BOTTOM)
                            
                            rotation = annotation.get('rotation', 0)
                            if rotation != 0:
                                img = img.rotate(-rotation, expand=True)
                            
                            # 🔥 고품질 리샘플링으로 크기 조정
                            img = img.resize((int(high_res_width), int(high_res_height)), Image.Resampling.LANCZOS)
                            
                            # 투명도 처리
                            opacity = annotation.get('opacity', 100) / 100.0
                            if opacity < 1.0 and img.mode == 'RGBA':
                                alpha = img.split()[-1]
                                alpha = alpha.point(lambda p: p * opacity)
                                img.putalpha(alpha)
                            
                            # 아웃라인 처리 (고해상도에 맞춰 스케일링)
                            if annotation.get('outline', False):
                                outline_width = int(annotation.get('outline_width', 3) * quality_multiplier)
                                outline_width = max(2, outline_width)  # 최소 두께 보장
                                new_size = (img.width + outline_width * 2, 
                                           img.height + outline_width * 2)
                                outlined_image = Image.new('RGBA', new_size, (0, 0, 0, 0))
                                
                                # 🔥 더 부드러운 아웃라인 그리기 (안티앨리어싱 효과)
                                for dx in range(-outline_width, outline_width + 1):
                                    for dy in range(-outline_width, outline_width + 1):
                                        distance = math.sqrt(dx*dx + dy*dy)
                                        if distance <= outline_width:
                                            # 거리에 따른 알파값 조정으로 부드러운 아웃라인
                                            alpha_factor = 1.0 - (distance / outline_width) * 0.3
                                            alpha_factor = max(0.7, min(1.0, alpha_factor))
                                            outline_color = (255, 255, 255, int(255 * alpha_factor))
                                            outlined_image.paste(outline_color, 
                                                               (outline_width + dx, outline_width + dy),
                                                               img)
                                
                                # 원본 이미지 중앙에 붙이기
                                outlined_image.paste(img, (outline_width, outline_width), img if img.mode == 'RGBA' else None)
                                img = outlined_image
                                # 좌표 조정은 실제 출력 크기 기준으로
                                x -= (outline_width * width / high_res_width)
                                y -= (outline_width * height / high_res_height)
                            
                            # 🔥 고품질 임시 파일로 이미지 저장 후 PDF에 그리기
                            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                                # RGB 모드로 변환 (PDF 호환성)
                                if img.mode == 'RGBA':
                                    # 투명한 배경을 흰색으로 변환 (고품질 알파 블렌딩)
                                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                                    if opacity < 1.0:
                                        # 투명도가 있는 경우 고품질 알파 블렌딩
                                        rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                    else:
                                        rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                    img = rgb_img
                                elif img.mode != 'RGB':
                                    img = img.convert('RGB')
                                
                                # 🔥 최고 품질로 저장 (압축 없음, 최적화 없음)
                                img.save(tmp_file.name, format='PNG', 
                                        optimize=False, compress_level=0, 
                                        pnginfo=None)  # 메타데이터 제거로 용량 최적화
                                
                                # PDF 좌표계에 맞춰 y 위치 조정
                                pdf_y = y - height
                                
                                # 🔥 고해상도 이미지를 원하는 크기로 출력 (품질 유지)
                                canvas.drawImage(tmp_file.name, x, pdf_y, width, height, 
                                               preserveAspectRatio=True, anchor='sw')
                                
                                try:
                                    os.unlink(tmp_file.name)
                                except:
                                    pass
                        
                        except Exception as e:
                            logger.debug(f"PDF 이미지 주석 그리기 오류: {e}")
                
                except Exception as e:
                    logger.debug(f"개별 벡터 주석 그리기 오류: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"벡터 주석 그리기 오류: {e}")
    
    def _fallback_pdf_page(self, canvas, item, index, page_width, page_height):
        """폴백 PDF 페이지 생성 - 하단 여백 축소"""
        try:
            combined_image = self.create_high_quality_combined_image(item)
            
            margin = 50
            max_width = page_width - (margin * 2)
            max_height = page_height - 65  # 🔥 하단 여백 대폭 축소 (기존 100 → 65)
            
            img_ratio = combined_image.width / combined_image.height
            
            if combined_image.width > max_width:
                new_width = max_width
                new_height = max_width / img_ratio
            else:
                new_width = combined_image.width
                new_height = combined_image.height
            
            if new_height > max_height:
                new_height = max_height
                new_width = max_height * img_ratio
            
            if new_width != combined_image.width or new_height != combined_image.height:
                combined_image = combined_image.resize((int(new_width), int(new_height)), 
                                                     Image.Resampling.LANCZOS)
            
            img_buffer = io.BytesIO()
            combined_image.save(img_buffer, format='PNG', optimize=False)
            img_buffer.seek(0)
            
            x_pos = (page_width - new_width) / 2
            y_pos = (page_height - new_height) / 2
            
            canvas.drawImage(ImageReader(img_buffer), x_pos, y_pos, new_width, new_height)
            
            # 🔥 페이지 번호 계산 (첫장 제외 시 조정)
            skip_title = getattr(self.app, 'skip_title_page', False) if self.app else False
            page_number = index + 1 if skip_title else index + 2
            
            canvas.setFont('Helvetica', 9)
            canvas.drawString(page_width - 80, 15, f"{page_number}")  # 페이지 번호 더 아래로 (20 → 15)
            
        except Exception as e:
            logger.error(f"폴백 PDF 페이지 생성 오류: {e}")
    
    def _add_feedback_text_to_pdf(self, canvas, item, index, y_position, text_area_height, page_width, margin):
        """PDF에 피드백 텍스트 추가 - 스마트 폰트 크기 적용"""
        try:
            feedback_text = item.get('feedback_text', '').strip()
            if not feedback_text:
                return
            
            korean_font = self.font_manager.register_pdf_font()
            
            # 기본 배경 박스 (원래대로 복구)
            canvas.setStrokeColorRGB(0.8, 0.8, 0.8)
            canvas.setFillColorRGB(0.98, 0.98, 0.98)
            canvas.rect(margin, y_position - text_area_height, 
                       page_width - (margin * 2), text_area_height, 
                       stroke=1, fill=1)
            
            # 제목 (원래대로 복구)
            canvas.setFillColorRGB(0.2, 0.2, 0.2)
            canvas.setFont(korean_font, 14)
            
            title_parts = []
            if self.app and hasattr(self.app, 'show_index_numbers') and self.app.show_index_numbers.get():
                title_parts.append(f"#{index + 1}")
            
            if self.app and hasattr(self.app, 'show_name') and self.app.show_name.get():
                title_parts.append(item.get('name', f'피드백 #{index + 1}'))
            
            if self.app and hasattr(self.app, 'show_timestamp') and self.app.show_timestamp.get():
                title_parts.append(f"({item.get('timestamp', '')})")
            
            title_text = " ".join(title_parts) if title_parts else f"피드백 #{index + 1}"
            
            title_y = y_position - 25
            canvas.drawString(margin + 10, title_y, f"💬 {title_text}")
            
            # 텍스트 영역
            canvas.setFillColorRGB(0.1, 0.1, 0.1)
            max_text_width = page_width - (margin * 2) - 20
            
            # 🔥 스마트 폰트 크기 자동 조정 (핵심 개선사항)
            available_height = text_area_height - 45  # 하단 여백 축소 (60 → 45)
            
            # 🔥 피드백 텍스트 폰트 크기 증가 - 최소치 상향 조정
            text_length = len(feedback_text)
            if text_length < 100:
                initial_font_size = 14  # 짧은 텍스트 (11→14)
            elif text_length < 300:
                initial_font_size = 13  # 중간 텍스트 (10→13)
            elif text_length < 600:
                initial_font_size = 12  # 긴 텍스트 (9→12)
            else:
                initial_font_size = 11  # 매우 긴 텍스트 (8→11)
            
            # 최적 폰트 크기 찾기
            best_font_size = initial_font_size
            best_line_height = 18  # 줄 간격도 조금 증가 (16→18)
            
            for font_size in range(initial_font_size, 10, -1):  # 최소 10까지 (7→10)
                canvas.setFont(korean_font, font_size)
                text_lines = self._wrap_text_for_pdf(feedback_text, max_text_width, korean_font, font_size, canvas)
                line_height = font_size + 5  # 적절한 줄 간격
                total_height = len(text_lines) * line_height
                
                if total_height <= available_height:
                    best_font_size = font_size
                    best_line_height = line_height
                    break
            
            # 최종 텍스트 렌더링
            canvas.setFont(korean_font, best_font_size)
            text_lines = self._wrap_text_for_pdf(feedback_text, max_text_width, korean_font, best_font_size, canvas)
            max_lines = int(available_height / best_line_height)
            
            text_y = title_y - 30
            
            for i, line in enumerate(text_lines):
                if i >= max_lines:
                    break
                if text_y < y_position - text_area_height + 2:  # 하단 여백 절반으로 축소 (5 → 2)
                    break
                canvas.drawString(margin + 15, text_y, line)
                text_y -= best_line_height
            
            # 텍스트가 잘렸을 때 표시
            if len(text_lines) > max_lines:
                canvas.setFont(korean_font, max(7, best_font_size - 1))
                canvas.setFillColorRGB(0.5, 0.5, 0.5)
                canvas.drawString(margin + 15, text_y + best_line_height, "... (내용이 더 있습니다)")
                
            logger.debug(f"스마트 폰트 적용: {best_font_size}pt, {len(text_lines)}줄")
        
        except Exception as e:
            logger.error(f"PDF 텍스트 추가 오류: {e}")
    
    def _wrap_text_for_pdf(self, text, max_width, font_name, font_size, canvas):
        """PDF용 텍스트 줄바꿈"""
        try:
            lines = []
            paragraphs = text.split('\n')
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    lines.append("")
                    continue
                
                words = paragraph.split()
                current_line = ""
                
                for word in words:
                    test_line = current_line + " " + word if current_line else word
                    
                    try:
                        text_width = canvas.stringWidth(test_line, font_name, font_size)
                        if text_width <= max_width:
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                            
                            if canvas.stringWidth(current_line, font_name, font_size) > max_width:
                                while current_line and canvas.stringWidth(current_line, font_name, font_size) > max_width:
                                    if len(current_line) > 1:
                                        lines.append(current_line[:-1] + "-")
                                        current_line = current_line[-1:]
                                    else:
                                        break
                    except:
                        if len(test_line) <= 50:
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                
                if current_line:
                    lines.append(current_line)
            
            return lines
            
        except Exception as e:
            logger.debug(f"텍스트 줄바꿈 오류: {e}")
            return [text[i:i+50] for i in range(0, len(text), 50)]

    def create_high_quality_combined_image_transparent(self, canvas, item, index, page_width, page_height):
        """투명도를 지원하는 합성 이미지 생성"""
        try:
            # 투명도를 완벽히 지원하는 합성 이미지 생성
            combined_image = self.create_high_quality_combined_image_with_transparency(item)
            
            # PDF에 추가
            margin = 50
            max_width = page_width - (margin * 2)
            max_height = page_height - 100
            
            img_ratio = combined_image.width / combined_image.height
            
            # 크기 계산
            if combined_image.width > max_width:
                new_width = max_width
                new_height = max_width / img_ratio
            else:
                new_width = combined_image.width
                new_height = combined_image.height
            
            if new_height > max_height:
                new_height = max_height
                new_width = max_height * img_ratio
            
            # 투명도를 유지한 채로 PNG 저장
            img_buffer = io.BytesIO()
            if combined_image.mode == 'RGBA':
                combined_image.save(img_buffer, format='PNG', optimize=False)
            else:
                combined_image.save(img_buffer, format='PNG', optimize=False)
            img_buffer.seek(0)
            
            x_pos = (page_width - new_width) / 2
            y_pos = (page_height - new_height) / 2
            
            # ReportLab은 PNG의 투명도를 자동으로 지원
            canvas.drawImage(ImageReader(img_buffer), x_pos, y_pos, new_width, new_height)
            
            logger.info(f"투명도 지원 PDF 페이지 생성 완료: {combined_image.mode}")
            
        except Exception as e:
            logger.error(f"투명도 지원 합성 오류: {e}")
            # 폴백
            self._fallback_pdf_page(canvas, item, index, page_width, page_height)

    def create_high_quality_combined_image_with_transparency(self, item):
        """투명도를 완벽히 지원하는 합성 이미지 생성"""
        try:
            original_image = item['image'].copy()
            annotations = item.get('annotations', [])
            
            # 투명도가 있는 주석이 있는지 확인
            has_transparency = any(
                ann.get('type') == 'image' and ann.get('opacity', 100) < 100
                for ann in annotations
            )
            
            if has_transparency:
                # RGBA 모드로 변환하여 투명도 지원
                if original_image.mode != 'RGBA':
                    original_image = original_image.convert('RGBA')
                
                # 투명 캔버스 생성
                final_image = Image.new('RGBA', original_image.size, (0, 0, 0, 0))
                final_image.paste(original_image, (0, 0))
                
                # PIL ImageDraw 사용
                draw = ImageDraw.Draw(final_image)
                
                # 투명도를 지원하는 주석 그리기
                for annotation in annotations:
                    if annotation.get('type') == 'image':
                        self._draw_transparent_image_annotation(final_image, annotation)
                    else:
                        # 다른 주석들은 기존 방식
                        self._draw_high_quality_annotation(draw, annotation, original_image.size)
                
                return final_image
            else:
                # 투명도가 없으면 기존 방식
                return self.create_high_quality_combined_image(item)
                
        except Exception as e:
            logger.error(f"투명도 지원 합성 이미지 생성 오류: {e}")
            return self.create_high_quality_combined_image(item)

    def _draw_transparent_image_annotation(self, base_image, annotation):
        """투명도를 완벽 지원하는 이미지 주석 그리기"""
        try:
            x = int(annotation['x'])
            y = int(annotation['y'])
            width = int(annotation['width'])
            height = int(annotation['height'])
            
            # base64 이미지 디코딩
            image_data = base64.b64decode(annotation['image_data'])
            img = Image.open(io.BytesIO(image_data))
            
            # 변형 적용
            if annotation.get('flip_horizontal', False):
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if annotation.get('flip_vertical', False):
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            
            rotation = annotation.get('rotation', 0)
            if rotation != 0:
                img = img.rotate(-rotation, expand=True)
            
            # 크기 조정
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            
            # 🔥 핵심: 투명도 적용 (흰색 배경과 합성하지 않음!)
            opacity = annotation.get('opacity', 100) / 100.0
            logger.info(f"🎨 투명도 처리: {opacity*100:.1f}%")
            
            if opacity < 1.0:
                # RGBA 모드로 변환
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # 🔥 중요: 기존 알파 채널에 투명도 곱하기 (흰색 배경과 합성 안함!)
                r, g, b, a = img.split()
                # 알파 채널에 투명도 곱하기
                new_alpha = a.point(lambda p: int(p * opacity))
                img = Image.merge('RGBA', (r, g, b, new_alpha))
                
                logger.info(f"✅ 투명도 {opacity*100:.1f}% 적용 완료 (RGBA 모드 유지)")
            else:
                # 100% 불투명이면 RGBA로만 변환
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                logger.debug("투명도 100%: RGBA 변환만 수행")
            
            # 아웃라인 처리 (RGBA 모드에서)
            if annotation.get('outline', False):
                outline_width = annotation.get('outline_width', 3)
                new_size = (img.width + outline_width * 2, 
                           img.height + outline_width * 2)
                
                # RGBA 배경으로 아웃라인 이미지 생성
                outlined_image = Image.new('RGBA', new_size, (0, 0, 0, 0))
                
                # 🔥 흰색 아웃라인 그리기 (ImageDraw 방식으로 완전히 개선)
                from PIL import ImageDraw
                draw = ImageDraw.Draw(outlined_image)
                
                # 중앙 위치 계산
                center_x = outline_width
                center_y = outline_width
                
                # 여러 겹의 흰색 테두리 생성 (UI 다이얼로그와 동일 방식)
                for i in range(outline_width):
                    # 바깥쪽부터 안쪽까지 흰색 테두리
                    alpha_factor = max(0.7, 1.0 - (i / outline_width) * 0.3)
                    outline_alpha = int(255 * alpha_factor * opacity)
                    
                    # 흰색 테두리 색상 (투명도 고려)
                    border_color = (255, 255, 255, outline_alpha)
                    
                    # 테두리 좌표 계산
                    left = center_x - outline_width + i
                    top = center_y - outline_width + i  
                    right = center_x + img.width + outline_width - i - 1
                    bottom = center_y + img.height + outline_width - i - 1
                    
                    # 테두리 그리기 (완전한 사각형 테두리)
                    draw.rectangle([left, top, right, bottom], outline=border_color, width=1)
                
                logger.debug(f"🔥 ImageDraw 흰색 아웃라인 완료: 두께 {outline_width}px, 투명도 {opacity:.2f}")
                
                # 원본 이미지를 중앙에 붙이기 (RGBA로 완전 투명도 지원)
                outlined_image.paste(img, (outline_width, outline_width), img)
                img = outlined_image
                x -= outline_width
                y -= outline_width
                
                logger.debug(f"아웃라인 적용 완료: 두께 {outline_width}px, 최종 크기 {img.size}")
            
            # 🔥 핵심: RGBA 이미지를 RGBA 베이스에 투명도와 함께 붙이기
            if base_image.mode == 'RGBA' and img.mode == 'RGBA':
                # 완벽한 알파 블렌딩
                base_image.paste(img, (x, y), img)  # 세 번째 인자가 마스크
                logger.info(f"✅ 투명도 {opacity*100:.1f}% 이미지 RGBA 합성 완료: 위치({x}, {y}), 크기{img.size}")
            else:
                logger.warning(f"⚠️ 모드 불일치: base={base_image.mode}, img={img.mode}")
                if img.mode == 'RGBA':
                    base_image.paste(img, (x, y), img)
                else:
                    base_image.paste(img, (x, y))
            
        except Exception as e:
            logger.error(f"투명도 이미지 주석 그리기 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def create_transparent_pdf_page(self, canvas, item, index, page_width, page_height):
        """투명도를 지원하는 PDF 페이지 생성"""
        try:
            logger.info(f"🎨 투명도 지원 PDF 페이지 생성 시작: {index+1}")
            
            # 🔥 투명도를 완벽히 지원하는 합성 이미지 생성
            combined_image = self.create_high_quality_combined_image_with_transparency(item)
            
            # 페이지 레이아웃 계산
            margin = 50
            feedback_text = item.get('feedback_text', '').strip()
            text_area_height = 0
            
            if feedback_text:
                # 텍스트 영역 높이 계산
                korean_font = self.font_manager.register_pdf_font()
                max_text_width = page_width - 100
                text_lines = self._wrap_text_for_pdf(feedback_text, max_text_width, korean_font, 11, canvas)
                line_height = 18
                title_space = 30  # 제목 공간 대폭 축소 (60 → 30)
                text_area_height = max(60, len(text_lines) * line_height + title_space + 20)  # 최소값 절반 축소 (120 → 60), 여백 절반 축소 (40 → 20)
                max_text_height = page_height * 0.4
                if text_area_height > max_text_height:
                    text_area_height = max_text_height
            
            # 이미지 영역 계산
            image_text_gap = 25
            usable_height = page_height - (margin * 2) - 60 - text_area_height - image_text_gap
            usable_width = page_width - (margin * 2)
            
            # 이미지 크기 조정
            img_ratio = combined_image.width / combined_image.height
            
            if combined_image.width > usable_width or combined_image.height > usable_height:
                if img_ratio > (usable_width / usable_height):
                    new_width = usable_width
                    new_height = usable_width / img_ratio
                else:
                    new_height = usable_height
                    new_width = usable_height * img_ratio
            else:
                new_width = combined_image.width
                new_height = combined_image.height
            
            # 이미지 위치 계산
            img_x = (page_width - new_width) / 2
            img_y = page_height - margin - new_height - 10
            
            # 🔥 핵심: PNG로 저장하여 투명도 유지
            logger.info(f"🎨 이미지 모드: {combined_image.mode}, 크기: {combined_image.size}")
            
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                # RGBA 모드면 PNG로 저장 (투명도 유지)
                if combined_image.mode == 'RGBA':
                    combined_image.save(tmp_file.name, format='PNG', optimize=False)
                    logger.info("✅ RGBA 이미지를 PNG로 저장 (투명도 유지)")
                else:
                    # RGB 모드면 고품질 PNG로 저장
                    high_res_width = int(new_width * 2)
                    high_res_height = int(new_height * 2)
                    if high_res_width != combined_image.width or high_res_height != combined_image.height:
                        combined_image = combined_image.resize((high_res_width, high_res_height), Image.Resampling.LANCZOS)
                    combined_image.save(tmp_file.name, format='PNG', optimize=False)
                    logger.info("✅ RGB 이미지를 고품질 PNG로 저장")
                
                # 🔥 ReportLab에서 PNG 투명도 지원
                canvas.drawImage(tmp_file.name, img_x, img_y, new_width, new_height, preserveAspectRatio=True)
                logger.info(f"✅ 투명도 지원 이미지 PDF 추가 완료: 위치({img_x:.1f}, {img_y:.1f}), 크기({new_width:.1f}x{new_height:.1f})")
                
                try:
                    os.unlink(tmp_file.name)
                except:
                    pass
            
            # 피드백 텍스트 추가
            if feedback_text:
                text_start_y = img_y - image_text_gap
                self._add_feedback_text_to_pdf(canvas, item, index, text_start_y, text_area_height, page_width, margin)
            
            # 꼬리말 및 페이지 번호
            if self.app and hasattr(self.app, 'project_footer') and self.app.project_footer.get():
                show_footer = True
                if hasattr(self.app, 'footer_first_page_only') and self.app.footer_first_page_only.get():
                    # 🔥 제목 페이지가 있을 때는 피드백 페이지에서 꼬리말 출력하지 않음
                    skip_title = getattr(self.app, 'skip_title_page', False)
                    if skip_title:
                        show_footer = (index == 0)  # 제목 페이지가 없으면 첫 번째 피드백 페이지에만 표시
                    else:
                        show_footer = False  # 제목 페이지가 있으면 피드백 페이지에서는 꼬리말 출력하지 않음
                
                if show_footer:
                    korean_font = self.font_manager.register_pdf_font()
                    canvas.setFont(korean_font, 10)
                    footer_text = self.app.project_footer.get().strip()
                    footer_width = canvas.stringWidth(footer_text, korean_font, 10)
                    canvas.drawString((page_width - footer_width) / 2, 15, footer_text)  # 꼬리말 더 아래로 (25 → 15)
            
            # 🔥 페이지 번호 계산 (첫장 제외 시 조정)
            skip_title = getattr(self.app, 'skip_title_page', False)
            page_number = index + 1 if skip_title else index + 2
            
            canvas.setFont('Helvetica', 10)
            canvas.drawString(page_width - 80, 15, f"- {page_number} -")  # 페이지 번호 더 아래로 (25 → 15)
            
            logger.info(f"🎨 투명도 지원 PDF 페이지 {index+1} 생성 완료")
            
        except Exception as e:
            logger.error(f"투명도 지원 PDF 페이지 생성 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 폴백
            self._fallback_pdf_page(canvas, item, index, page_width, page_height)

class CanvasNavigationBar:
    """캔버스 네비게이션 바 클래스"""
    def __init__(self, parent, app_instance):
        self.parent = parent
        self.app = app_instance
        self.canvas = None
        self.minimap_items = []
        self.current_viewport = None
        self.nav_width = 180  # 120 -> 180으로 확대
        self.nav_height = 350  # 300 -> 350으로 확대
        self.item_height = 50  # 40 -> 50으로 확대
        self.margin = 8  # 5 -> 8로 확대
        
        self.create_navigation_bar()
        
    def create_navigation_bar(self):
        """네비게이션 바 생성"""
        # 네비게이션 프레임 - 메인 UI와 일관성 있는 스타일 (좌우 여백 균등)
        self.nav_frame = tk.LabelFrame(self.parent, text="네비게이션", 
                                      bg='white', 
                                      font=self.app.font_manager.ui_font_bold,
                                      fg='#333',
                                      relief='flat', bd=1, highlightbackground='#e0e0e0', 
                                      highlightthickness=1,
                                      padx=6, pady=8,  # 좌우 패딩 조정
                                      width=self.nav_width)
        self.nav_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 8), pady=0)  # 좌우 여백 균등하게
        self.nav_frame.pack_propagate(False)
        
        # 상단 정보 라벨 - 통일된 폰트 사용
        self.info_label = tk.Label(self.nav_frame, text="총 0개", 
                                  bg='white', fg='#495057',
                                  font=self.app.font_manager.ui_font)
        self.info_label.pack(pady=(0, 8))
        
        # 미니맵 캔버스 컨테이너
        canvas_container = tk.Frame(self.nav_frame, bg='white')
        canvas_container.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        # 미니맵 캔버스 - 선택시에도 회색 테두리 유지
        self.canvas = tk.Canvas(canvas_container, bg='#ced4da', 
                               highlightthickness=1, 
                               highlightbackground='#6c757d',
                               highlightcolor='#6c757d',
                               relief='flat', bd=1,
                               width=self.nav_width-28,  # 좌우 여백을 위한 공간 확보
                               height=self.nav_height)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 4))  # 좌우 여백 균등하게
        
        # 스크롤바 - 메인 UI와 일관성 있는 크기
        scrollbar = tk.Scrollbar(canvas_container, orient=tk.VERTICAL, 
                                command=self.canvas.yview, width=20)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # 이벤트 바인딩
        self.canvas.bind('<Button-1>', self.on_minimap_click)
        self.canvas.bind('<MouseWheel>', self.on_minimap_scroll)
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        # 하단 컨트롤 프레임
        control_frame = tk.Frame(self.nav_frame, bg='white')
        control_frame.pack(fill=tk.X, pady=(0, 0))
        
        # 이전/다음 버튼 컨테이너
        btn_frame = tk.Frame(control_frame, bg='white')
        btn_frame.pack(expand=True)
        
        # 이전/다음 버튼 - 화살표만 표시 (더 작은 크기)
        button_style = {
            'bg': 'white', 'fg': '#2196F3',
            'relief': 'flat', 'bd': 0,
            'activebackground': '#e3f2fd',
            'activeforeground': '#2196F3',
            'font': ('Malgun Gothic', 10, 'bold'),  # 14 -> 10으로 폰트 크기 축소
            'width': 2, 'height': 1,  # 3 -> 2로 버튼 너비 축소
            'padx': 3, 'pady': 2  # 6,4 -> 3,2로 패딩 축소
        }
        
        self.prev_btn = tk.Button(btn_frame, text="◀", command=self.go_previous, **button_style)
        self.prev_btn.pack(side=tk.LEFT, padx=3)
        
        self.next_btn = tk.Button(btn_frame, text="▶", command=self.go_next, **button_style)
        self.next_btn.pack(side=tk.LEFT, padx=3)
        
    def refresh_minimap(self):
        """미니맵 새로고침"""
        if not self.canvas:
            return
            
        self.canvas.delete("all")
        self.minimap_items.clear()
        
        if not self.app.feedback_items:
            self.info_label.config(text="📄 피드백 없음", fg='#6c757d')
            self.update_navigation_buttons()
            return
            
        total_items = len(self.app.feedback_items)
        current_pos = self.app.current_index + 1
        self.info_label.config(text=f"📊 총 {total_items}개 | 현재 {current_pos}번째", fg='#495057')
        
        # 미니맵 아이템 그리기
        canvas_width = self.canvas.winfo_width() or (self.nav_width - 25)
        y_pos = self.margin
        
        for i, item in enumerate(self.app.feedback_items):
            # 현재 선택된 항목 표시
            is_current = (i == self.app.current_index)
            
            # 개선된 색상 스키마
            if is_current:
                bg_color = '#2196F3'  # 메인 UI와 일관성 있는 파란색
                text_color = 'white'
                border_color = '#1976D2'
                shadow_color = '#e3f2fd'
            else:
                bg_color = '#ffffff'
                text_color = '#333333'
                border_color = '#dee2e6'
                shadow_color = '#f8f9fa'
            
            # 미니맵 아이템 그리기 - 더 큰 영역
            x1, y1 = self.margin, y_pos
            x2, y2 = canvas_width - self.margin, y_pos + self.item_height
            
            # 그림자 효과 (선택된 항목만)
            if is_current:
                shadow_rect = self.canvas.create_rectangle(x1 + 2, y1 + 2, x2 + 2, y2 + 2,
                                                         fill=shadow_color, outline='', width=0)
            
            # 배경 사각형 - 둥근 모서리 효과
            rect_id = self.canvas.create_rectangle(x1, y1, x2, y2,
                                                  fill=bg_color, outline=border_color,
                                                  width=2 if is_current else 1)
            
            # 텍스트 (이름) - 더 큰 글자와 적절한 길이
            text = item.get('name', f'피드백 {i+1}')
            if len(text) > 18:  # 12 -> 18로 확장
                text = text[:18] + '...'
                
            # 메인 제목 - 더 큰 폰트
            text_id = self.canvas.create_text(x1 + 8, y1 + 8, text=text,
                                            anchor='nw', fill=text_color,
                                            font=('Malgun Gothic', 10, 'bold' if is_current else 'normal'))
            
            # 주석 개수 표시 - 개선된 위치와 스타일
            annotation_count = len(item.get('annotations', []))
            if annotation_count > 0:
                count_text = f"📝 {annotation_count}개"
                self.canvas.create_text(x2 - 8, y1 + 8, text=count_text,
                                      anchor='ne', fill=text_color,
                                      font=('Malgun Gothic', 8))
            
            # 인덱스 정보 표시
            index_text = f"#{i+1}"
            self.canvas.create_text(x1 + 8, y2 - 8, text=index_text,
                                  anchor='sw', fill=text_color,
                                  font=('Malgun Gothic', 9, 'bold'))
            
            # 미니맵 아이템 정보 저장
            self.minimap_items.append({
                'index': i,
                'rect_id': rect_id,
                'bounds': (x1, y1, x2, y2)
            })
            
            y_pos += self.item_height + self.margin
        
        # 스크롤 영역 설정
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # 네비게이션 버튼 상태 업데이트
        self.update_navigation_buttons()
        
        # 현재 항목으로 스크롤
        self.scroll_to_current()
        
    def on_minimap_click(self, event):
        """미니맵 클릭 이벤트"""
        canvas_y = self.canvas.canvasy(event.y)
        
        for item in self.minimap_items:
            x1, y1, x2, y2 = item['bounds']
            if y1 <= canvas_y <= y2:
                # 선택된 피드백으로 이동
                self.app.current_index = item['index']
                self.app.scroll_to_card(item['index'])
                self.app.update_status()
                self.refresh_minimap()
                break
                
    def on_minimap_scroll(self, event):
        """미니맵 스크롤 이벤트"""
        self.canvas.yview_scroll(int(1 * (event.delta / 120)), "units")
        
    def on_canvas_configure(self, event):
        """캔버스 크기 변경 이벤트"""
        # 크기 변경시 미니맵 새로고침 (너무 자주 호출되지 않도록 딜레이)
        if hasattr(self, '_refresh_timer'):
            self.app.root.after_cancel(self._refresh_timer)
        self._refresh_timer = self.app.root.after(100, self.refresh_minimap)
        
    def scroll_to_current(self):
        """현재 선택된 항목으로 스크롤"""
        if not self.minimap_items or self.app.current_index >= len(self.minimap_items):
            return
            
        current_item = self.minimap_items[self.app.current_index]
        x1, y1, x2, y2 = current_item['bounds']
        
        # 캔버스의 현재 보이는 영역
        canvas_height = self.canvas.winfo_height()
        if canvas_height <= 1:
            return
            
        top = self.canvas.canvasy(0)
        bottom = top + canvas_height
        
        # 현재 항목이 보이지 않으면 스크롤
        if y1 < top or y2 > bottom:
            # 항목을 중앙에 위치시키기
            target_y = max(0, y1 - canvas_height // 2)
            bbox = self.canvas.bbox("all")
            if bbox:
                total_height = bbox[3] - bbox[1]
                if total_height > 0:
                    fraction = target_y / total_height
                    self.canvas.yview_moveto(fraction)
                
    def go_previous(self):
        """이전 피드백으로 이동"""
        if self.app.current_index > 0:
            self.app.current_index -= 1
            self.app.scroll_to_card(self.app.current_index)
            self.app.update_status()
            self.refresh_minimap()
            
    def go_next(self):
        """다음 피드백으로 이동"""
        if self.app.current_index < len(self.app.feedback_items) - 1:
            self.app.current_index += 1
            self.app.scroll_to_card(self.app.current_index)
            self.app.update_status()
            self.refresh_minimap()
            
    def update_navigation_buttons(self):
        """네비게이션 버튼 상태 업데이트"""
        if hasattr(self, 'prev_btn') and hasattr(self, 'next_btn'):
            # 이전 버튼
            if self.app.current_index <= 0 or not self.app.feedback_items:
                self.prev_btn.config(state='disabled', 
                                    bg='#f8f9fa', fg='#adb5bd',
                                    relief='flat', bd=0)
            else:
                self.prev_btn.config(state='normal',
                                    bg='white', fg='#2196F3',
                                    relief='flat', bd=0)
                
            # 다음 버튼
            if (self.app.current_index >= len(self.app.feedback_items) - 1 or 
                not self.app.feedback_items):
                self.next_btn.config(state='disabled',
                                    bg='#f8f9fa', fg='#adb5bd',
                                    relief='flat', bd=0)
            else:
                self.next_btn.config(state='normal',
                                    bg='white', fg='#2196F3',
                                    relief='solid', bd=0)

class PDFInfoDialog:
    """PDF 정보 입력 다이얼로그 - 페이지 크기 옵션 추가"""
    
    def __init__(self, parent, app_instance):
        self.parent = parent
        self.app = app_instance
        self.result = None
        self.dialog = None
        self.desc_text = None
        
        # 현재 값들을 가져와서 기본값으로 설정
        self.project_title = tk.StringVar(value=app_instance.project_title.get())
        self.project_to = tk.StringVar(value=app_instance.project_to.get())
        self.project_from = tk.StringVar(value=app_instance.project_from.get())
        self.project_description = tk.StringVar(value=app_instance.project_description.get())
        self.project_footer = tk.StringVar(value=app_instance.project_footer.get())
        self.footer_first_page_only = tk.BooleanVar(value=app_instance.footer_first_page_only.get())
        
        # 🔥 새로운 페이지 크기 옵션 추가
        self.pdf_page_mode = tk.StringVar(value=getattr(app_instance, 'pdf_page_mode', 'A4'))
        
        # PDF 가독성 내보내기 옵션
        self.pdf_readability_mode = tk.BooleanVar(value=False)
        
        # 🔥 첫장 제외하기 옵션 추가
        self.skip_title_page = tk.BooleanVar(value=getattr(app_instance, 'skip_title_page', False))
        
        self.create_dialog()
    
    def create_dialog(self):
        """PDF 정보 입력 대화상자 생성"""
        try:
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title("PDF 내보내기 설정")
            
            # 🔥 화면 해상도에 따른 적응형 크기 설정
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            # 기본 크기 계산 (화면 크기의 40% 너비, 80% 높이, 최소/최대 제한)
            dialog_width = max(600, min(800, int(screen_width * 0.4)))
            dialog_height = max(600, min(1000, int(screen_height * 0.8)))
            
            self.dialog.geometry(f"{dialog_width}x{dialog_height}")
            self.dialog.resizable(True, True)  # 🔥 크기 조정 가능
            self.dialog.minsize(550, 500)      # 🔥 최소 크기 설정
            self.dialog.maxsize(1000, int(screen_height * 0.9))  # 🔥 최대 크기 설정
            self.dialog.configure(bg='white')

            # 🔥 스크롤 가능한 메인 프레임 생성
            canvas_frame = tk.Frame(self.dialog, bg='white')
            canvas_frame.pack(fill=tk.BOTH, expand=True)
            
            # 캔버스와 스크롤바
            main_canvas = tk.Canvas(canvas_frame, bg='white', highlightthickness=0)
            scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=main_canvas.yview)
            self.scrollable_main_frame = tk.Frame(main_canvas, bg='white')
            
            # 스크롤바 설정
            self.scrollable_main_frame.bind(
                "<Configure>",
                lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
            )
            
            main_canvas.create_window((0, 0), window=self.scrollable_main_frame, anchor="nw")
            main_canvas.configure(yscrollcommand=scrollbar.set)
            
            # 마우스 휠 스크롤 지원
            def _on_mousewheel(event):
                main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            main_canvas.bind("<MouseWheel>", _on_mousewheel)
            
            # 스크롤바와 캔버스 배치
            main_canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # 실제 콘텐츠가 들어갈 프레임
            main_frame = tk.Frame(self.scrollable_main_frame, bg='white')
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            # 제목 섹션 (기존과 동일)
            title_section = tk.LabelFrame(main_frame, text="문서 정보", bg='white', 
                                        font=self.app.font_manager.ui_font)
            title_section.pack(fill=tk.X, pady=(0, 15))

            tk.Label(title_section, text="제목:", bg='white', 
                    font=self.app.font_manager.ui_font).pack(anchor=tk.W, padx=10, pady=(10, 5))
            title_entry = tk.Entry(title_section, textvariable=self.project_title, 
                                 font=self.app.font_manager.ui_font, width=60)
            title_entry.pack(fill=tk.X, padx=10, pady=(0, 10))

            # 🔥 페이지 크기 설정 섹션 추가
            size_section = tk.LabelFrame(main_frame, text="페이지 크기 설정", bg='white',
                                       font=self.app.font_manager.ui_font)
            size_section.pack(fill=tk.X, pady=(0, 15))
            
            # 라디오 버튼들
            tk.Radiobutton(size_section, text="📄 A4 고정 (표준, 210×297mm)", 
                          variable=self.pdf_page_mode, value='A4',
                          bg='white', font=self.app.font_manager.ui_font,
                          command=self.update_page_preview).pack(anchor=tk.W, padx=10, pady=5)
            
            tk.Radiobutton(size_section, text="📐 이미지 크기에 맞춤 (권장)", 
                          variable=self.pdf_page_mode, value='adaptive',
                          bg='white', font=self.app.font_manager.ui_font,
                          command=self.update_page_preview).pack(anchor=tk.W, padx=10, pady=5)
            
            # 미리보기 정보
            self.page_preview = tk.Label(size_section, text="", bg='white', fg='#666',
                                       font=(self.app.font_manager.ui_font[0], 9))
            self.page_preview.pack(anchor=tk.W, padx=25, pady=(0, 10))

            # 수신자/발신자 섹션 (기존과 동일)
            sender_section = tk.LabelFrame(main_frame, text="수신자/발신자 정보", bg='white',
                                         font=self.app.font_manager.ui_font)
            sender_section.pack(fill=tk.X, pady=(0, 15))

            tk.Label(sender_section, text="수신:", bg='white',
                    font=self.app.font_manager.ui_font).pack(anchor=tk.W, padx=10, pady=(10, 5))
            to_entry = tk.Entry(sender_section, textvariable=self.project_to,
                              font=self.app.font_manager.ui_font, width=60)
            to_entry.pack(fill=tk.X, padx=10, pady=(0, 10))

            tk.Label(sender_section, text="발신:", bg='white',
                    font=self.app.font_manager.ui_font).pack(anchor=tk.W, padx=10, pady=(0, 5))
            from_entry = tk.Entry(sender_section, textvariable=self.project_from,
                                 font=self.app.font_manager.ui_font, width=60)
            from_entry.pack(fill=tk.X, padx=10, pady=(0, 10))

            # 설명 섹션 (기존과 동일)
            desc_section = tk.LabelFrame(main_frame, text="문서 설명", bg='white',
                                       font=self.app.font_manager.ui_font)
            desc_section.pack(fill=tk.X, pady=(0, 15))

            tk.Label(desc_section, text="설명:", bg='white',
                    font=self.app.font_manager.ui_font).pack(anchor=tk.W, padx=10, pady=(10, 5))
            
            desc_container = tk.Frame(desc_section, bg='white')
            desc_container.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            self.desc_text = tk.Text(desc_container, height=6, width=60, wrap=tk.WORD,
                                   font=self.app.font_manager.ui_font)
            desc_scrollbar = tk.Scrollbar(desc_container, orient=tk.VERTICAL, command=self.desc_text.yview)
            self.desc_text.configure(yscrollcommand=desc_scrollbar.set)
            
            self.desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            desc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            self.desc_text.insert('1.0', self.app.project_description.get())
            self.desc_text.bind('<KeyRelease>', lambda e: self.app.project_description.set(self.desc_text.get('1.0', tk.END).strip()))

            # 꼬리말 섹션 (기존과 동일)
            footer_section = tk.LabelFrame(main_frame, text="꼬리말", bg='white',
                                         font=self.app.font_manager.ui_font)
            footer_section.pack(fill=tk.X, pady=(0, 15))

            tk.Label(footer_section, text="꼬리말:", bg='white',
                    font=self.app.font_manager.ui_font).pack(anchor=tk.W, padx=10, pady=(10, 5))
            
            footer_entry = tk.Entry(footer_section, textvariable=self.project_footer,
                                  font=self.app.font_manager.ui_font, width=60)
            footer_entry.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            footer_option = tk.Checkbutton(footer_section, text="첫 장에만 꼬리말 출력",
                                         variable=self.footer_first_page_only,
                                         bg='white', font=self.app.font_manager.ui_font)
            footer_option.pack(anchor=tk.W, padx=10, pady=(0, 10))

            # 가독성 옵션 섹션
            readability_section = tk.LabelFrame(main_frame, text="가독성 옵션", bg='white',
                                              font=self.app.font_manager.ui_font)
            readability_section.pack(fill=tk.X, pady=(0, 15))
            
            readability_option = tk.Checkbutton(readability_section, 
                                              text="📖 가독성 내보내기 (텍스트 배경 + 주석 흰색 아웃라인)",
                                              variable=self.pdf_readability_mode,
                                              bg='white', font=self.app.font_manager.ui_font)
            readability_option.pack(anchor=tk.W, padx=10, pady=10)
            
            # 설명 텍스트
            readability_desc = tk.Label(readability_section, 
                                      text="※ 복잡한 배경에서 주석의 가독성을 향상시킵니다.",
                                      bg='white', fg='#666', 
                                      font=(self.app.font_manager.ui_font[0], 9))
            readability_desc.pack(anchor=tk.W, padx=25, pady=(0, 10))

            # 🔥 페이지 구성 옵션 섹션 추가
            page_section = tk.LabelFrame(main_frame, text="페이지 구성", bg='white',
                                        font=self.app.font_manager.ui_font)
            page_section.pack(fill=tk.X, pady=(0, 15))
            
            skip_title_option = tk.Checkbutton(page_section, 
                                             text="📄 첫장 제외하기 (제목 페이지 생략)",
                                             variable=self.skip_title_page,
                                             bg='white', font=self.app.font_manager.ui_font)
            skip_title_option.pack(anchor=tk.W, padx=10, pady=10)
            
            # 설명 텍스트
            skip_title_desc = tk.Label(page_section, 
                                     text="※ 제목 페이지 없이 피드백 이미지들만 PDF로 생성됩니다.",
                                     bg='white', fg='#666', 
                                     font=(self.app.font_manager.ui_font[0], 9))
            skip_title_desc.pack(anchor=tk.W, padx=25, pady=(0, 10))

            # 버튼 섹션 (기존과 동일)
            button_frame = tk.Frame(main_frame, bg='white')
            button_frame.pack(fill=tk.X, pady=(20, 0))

            cancel_btn = tk.Button(button_frame, text="취소", command=self.cancel,
                                 font=self.app.font_manager.ui_font,
                                 bg='white', fg='#666666', 
                                 relief='solid', bd=1,
                                 padx=20, pady=8,
                                 activebackground='#f5f5f5',
                                 activeforeground='#666666')
            cancel_btn.pack(side=tk.LEFT)

            export_btn = tk.Button(button_frame, text="PDF 내보내기", command=self.generate_pdf,
                                 font=self.app.font_manager.ui_font,
                                 bg='white', fg='#2196F3',
                                 relief='solid', bd=1,
                                 padx=25, pady=8,
                                 activebackground='#e3f2fd',
                                 activeforeground='#2196F3')
            export_btn.pack(side=tk.RIGHT)

            # 🔥 스마트 창 위치 조정 - 화면 경계 고려
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
            
            self.dialog.update_idletasks()
            dialog_width = self.dialog.winfo_width()
            dialog_height = self.dialog.winfo_height()
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            try:
                parent_x = self.parent.winfo_x()
                parent_y = self.parent.winfo_y()
                parent_width = self.parent.winfo_width()
                parent_height = self.parent.winfo_height()
                
                # 부모 창 중앙 계산
                x = parent_x + (parent_width - dialog_width) // 2
                y = parent_y + (parent_height - dialog_height) // 2
            except tk.TclError:
                # 부모 창 정보를 가져올 수 없는 경우 화면 중앙으로
                x = (screen_width - dialog_width) // 2
                y = (screen_height - dialog_height) // 2
            
            # 화면 경계 확인 및 조정
            margin = 20
            if x + dialog_width > screen_width - margin:
                x = screen_width - dialog_width - margin
            if x < margin:
                x = margin
            if y + dialog_height > screen_height - 60:  # 작업 표시줄 고려
                y = screen_height - dialog_height - 60
            if y < margin:
                y = margin
            
            self.dialog.geometry(f"+{x}+{y}")

            title_entry.focus_set()
            
            # 초기 미리보기 업데이트
            self.update_page_preview()

        except Exception as e:
            logger.error(f"PDF 정보 대화상자 생성 오류: {e}")
            messagebox.showerror("오류", "PDF 정보 대화상자를 생성하는 중 오류가 발생했습니다.")
    
    def update_page_preview(self):
        """페이지 크기 미리보기 업데이트 - 세로 긴 이미지 정보 포함"""
        try:
            mode = self.pdf_page_mode.get()
            
            if mode == 'A4':
                preview_text = "모든 페이지가 A4 크기(210×297mm)로 생성됩니다."
            else:  # adaptive
                if hasattr(self.app, 'feedback_items') and self.app.feedback_items:
                    total_items = len(self.app.feedback_items)
                    
                    # 🔥 이미지 유형 분석
                    a4_ratio = 210.0 / 297.0  # ≈ 0.707
                    tall_images = 0  # 세로가 긴 이미지 수
                    wide_images = 0  # 가로가 긴 이미지 수
                    normal_images = 0  # 일반 비율 이미지 수
                    
                    for item in self.app.feedback_items:
                        img_w, img_h = item['image'].size
                        img_ratio = img_w / img_h
                        
                        if img_ratio < a4_ratio * 0.8:  # A4보다 훨씬 세로가 긴 이미지
                            tall_images += 1
                        elif img_ratio > a4_ratio * 1.5:  # A4보다 훨씬 가로가 긴 이미지  
                            wide_images += 1
                        else:
                            normal_images += 1
                    
                    # 첫 번째 이미지 크기 예시
                    first_item = self.app.feedback_items[0]
                    img_w, img_h = first_item['image'].size
                    img_ratio = img_w / img_h
                    
                    
                    # 🔥 실제 PDF 생성과 동일한 DPI 사용
                    dpi = getattr(self.app, 'pdf_quality', None)
                    if dpi is None or not hasattr(dpi, 'get'):
                        dpi = 150  # 기본값
                    else:
                        dpi = dpi.get()
                    
                    # 대략적인 페이지 크기 계산 (실제 DPI 사용)
                    page_w_mm = int((img_w / dpi) * 25.4) + 4  # 🔥 여백 통일 (20→4mm)
                    page_h_mm = int((img_h / dpi) * 25.4) + 4
                    
                    # 🔥 세로 긴 이미지에 대한 추가 정보
                    if img_ratio < a4_ratio:
                        is_tall = " (세로 긴 이미지 최적화)"
                    else:
                        is_tall = ""
                    
                    preview_lines = [
                        f"각 이미지 크기에 맞춰 생성됩니다.",
                        f"예시: 첫 번째 이미지 → 약 {page_w_mm}×{page_h_mm}mm{is_tall}",
                        f"총 {total_items}개 페이지"
                    ]
                    
                    # 🔥 이미지 유형별 통계 추가
                    if tall_images > 0 or wide_images > 0:
                        type_info = []
                        if tall_images > 0:
                            type_info.append(f"세로형 {tall_images}개")
                        if normal_images > 0:
                            type_info.append(f"일반형 {normal_images}개")
                        if wide_images > 0:
                            type_info.append(f"가로형 {wide_images}개")
                        
                        preview_lines.append(f"구성: {', '.join(type_info)}")
                    
                    # 🔥 세로 긴 이미지 특별 안내
                    if tall_images > 0:
                        preview_lines.append("※ 세로 긴 이미지는 원본 크기 기준으로 최적화됩니다")
                    
                    preview_text = "\n".join(preview_lines)
                else:
                    preview_text = "이미지별로 최적화된 크기로 생성됩니다.\n※ 세로 긴 이미지는 원본 비율을 유지합니다"
            
            self.page_preview.config(text=preview_text)
            
        except Exception as e:
            logger.debug(f"페이지 미리보기 업데이트 오류: {e}")
    
    def generate_pdf(self):
        """PDF 생성 실행"""
        try:
            # 입력된 정보 수집
            description = self.desc_text.get('1.0', tk.END).strip()
            footer = self.project_footer.get().strip()
            
            self.result = {
                'title': self.project_title.get(),
                'to': self.project_to.get(),
                'from': self.project_from.get(),
                'description': description,
                'footer': footer,
                'footer_first_page_only': self.footer_first_page_only.get(),
                'pdf_page_mode': self.pdf_page_mode.get(),  # 🔥 중요: 페이지 모드 포함
                'pdf_readability_mode': self.pdf_readability_mode.get(),  # 가독성 모드 추가
                'skip_title_page': self.skip_title_page.get()  # 🔥 첫장 제외하기 옵션 추가
            }
            
            # 앱의 설정값들 업데이트
            self.app.project_title.set(self.result['title'])
            self.app.project_to.set(self.result['to'])
            self.app.project_from.set(self.result['from'])
            self.app.project_description.set(self.result['description'])
            self.app.project_footer.set(self.result['footer'])
            self.app.footer_first_page_only.set(self.result['footer_first_page_only'])
            
            # 🔥 중요: 페이지 모드 설정 저장
            self.app.pdf_page_mode = self.result['pdf_page_mode']
            
            # 가독성 모드 설정 저장
            self.app.pdf_readability_mode = self.result['pdf_readability_mode']
            
            # 첫장 제외하기 설정 저장
            self.app.skip_title_page = self.result['skip_title_page']
            
            self.dialog.destroy()
            
            # PDF 생성 시작
            self.app.start_pdf_generation()
            
        except Exception as e:
            logger.error(f"PDF 정보 수집 오류: {e}")
            messagebox.showerror('오류', f'정보 수집 중 오류가 발생했습니다: {str(e)}')
    
    def cancel(self):
        """취소"""
        self.result = None
        self.dialog.destroy()

class CanvasExtensionDialog:
    """캔버스 영역 확장 다이얼로그 - 수정된 버전"""
    
    def __init__(self, parent, app_instance):
        self.parent = parent
        self.app = app_instance
        self.result = None
        self.dialog = None
        
        # 설정 변수
        self.direction = tk.StringVar(value='right')
        self.percentage = tk.IntVar(value=50)
        self.bg_color = tk.StringVar(value='#ffffff')
        self.transparent = tk.BooleanVar(value=False)
        
        self.create_dialog()
    
    def create_dialog(self):
        """영역확장 대화상자 생성 - 수정된 버전"""
        try:
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title("영역 확장")
            
            # 🔥 아이콘 설정
            setup_window_icon(self.dialog)
            
            # 🔥 화면 해상도에 따른 적응형 크기 설정
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            # 기본 크기 계산 (화면 크기 고려, 최소/최대 제한)
            dialog_width = max(450, min(600, int(screen_width * 0.35)))
            dialog_height = max(500, min(700, int(screen_height * 0.6)))
            
            self.dialog.geometry(f"{dialog_width}x{dialog_height}")
            self.dialog.resizable(True, True)  # 🔥 크기 조정 가능
            self.dialog.minsize(400, 450)      # 🔥 최소 크기 설정
            self.dialog.maxsize(800, int(screen_height * 0.8))  # 🔥 최대 크기 설정
            self.dialog.configure(bg='white')
            
            # 🔥 중요: 창 닫기 이벤트 처리 추가
            self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
            
            main_frame = tk.Frame(self.dialog, bg='white')
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # 방향 설정 섹션
            direction_frame = tk.LabelFrame(main_frame, text="확장 방향", bg='white',
                                          font=self.app.font_manager.ui_font_bold)
            direction_frame.pack(fill=tk.X, pady=(0, 15))
            
            directions = [
                ('오른쪽', 'right', '➡️'),
                ('아래', 'down', '⬇️'),
                ('왼쪽', 'left', '⬅️'),
                ('위', 'up', '⬆️')
            ]
            
            for text, value, icon in directions:
                rb = tk.Radiobutton(direction_frame, text=f"{icon} {text}", 
                                   variable=self.direction, value=value,
                                   bg='white', font=self.app.font_manager.ui_font)
                rb.pack(side=tk.LEFT, padx=10, pady=10)
            
            # 크기 설정 섹션
            size_frame = tk.LabelFrame(main_frame, text="확장 크기", bg='white',
                                     font=self.app.font_manager.ui_font_bold)
            size_frame.pack(fill=tk.X, pady=(0, 15))
            
            size_container = tk.Frame(size_frame, bg='white')
            size_container.pack(fill=tk.X, padx=10, pady=10)
            
            tk.Label(size_container, text="현재 크기 대비:", bg='white',
                    font=self.app.font_manager.ui_font).pack(side=tk.LEFT)
            
            # 퍼센트 선택 콤보박스
            percentages = [20, 40, 50, 80, 100, 150, 200]
            percent_combo = ttk.Combobox(size_container, textvariable=self.percentage,
                                        values=percentages, width=10, state='readonly')
            percent_combo.set(50)
            percent_combo.pack(side=tk.LEFT, padx=(5, 2))
            
            tk.Label(size_container, text="%", bg='white',
                    font=self.app.font_manager.ui_font).pack(side=tk.LEFT)
            
            # 미리보기 라벨
            self.preview_label = tk.Label(size_frame, text="", bg='white', fg='#666',
                                        font=self.app.font_manager.ui_font_small)
            self.preview_label.pack(pady=(5, 10))
            
            # 배경색 설정 섹션
            bg_frame = tk.LabelFrame(main_frame, text="배경 설정", bg='white',
                                   font=self.app.font_manager.ui_font_bold)
            bg_frame.pack(fill=tk.X, pady=(0, 15))
            
            bg_container = tk.Frame(bg_frame, bg='white')
            bg_container.pack(fill=tk.X, padx=10, pady=10)
            
            # 배경색 선택
            color_frame = tk.Frame(bg_container, bg='white')
            color_frame.pack(fill=tk.X, pady=(0, 5))
            
            tk.Label(color_frame, text="배경색:", bg='white',
                    font=self.app.font_manager.ui_font).pack(side=tk.LEFT)
            
            self.color_button = tk.Button(color_frame, text="  ", bg=self.bg_color.get(),
                                        width=4, height=1, command=self.choose_color,
                                        relief='solid', bd=1)
            self.color_button.pack(side=tk.LEFT, padx=(10, 0))
            
            # 투명 배경 체크박스
            trans_check = tk.Checkbutton(bg_container, text="투명 배경 (32bit)",
                                        variable=self.transparent,
                                        command=self.toggle_transparent,
                                        bg='white', font=self.app.font_manager.ui_font)
            trans_check.pack(fill=tk.X, pady=(5, 0))
            
            # 버튼 섹션
            button_frame = tk.Frame(main_frame, bg='white')
            button_frame.pack(fill=tk.X, pady=(20, 0))
            
            # 취소 버튼
            cancel_btn = tk.Button(button_frame, text="취소", command=self.cancel,
                                 font=self.app.font_manager.ui_font,
                                 bg='white', fg='#666666',
                                 relief='solid', bd=1,
                                 padx=20, pady=8)
            cancel_btn.pack(side=tk.LEFT)
            
            # 🔥 확장 버튼 - 명확한 이벤트 처리
            extend_btn = tk.Button(button_frame, text="확장 생성!", 
                                 command=self.extend_with_debug,  # 디버깅 포함된 메서드
                                 font=self.app.font_manager.ui_font_bold,
                                 bg='white', fg='#4CAF50',
                                 relief='solid', bd=1,
                                 padx=25, pady=8)
            extend_btn.pack(side=tk.RIGHT)
            
            # 대화상자 중앙 배치
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
            
            # 🔥 스마트 창 위치 조정 - 화면 경계 고려
            self.dialog.update_idletasks()
            dialog_width = self.dialog.winfo_width()
            dialog_height = self.dialog.winfo_height()
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            try:
                parent_x = self.parent.winfo_x()
                parent_y = self.parent.winfo_y()
                parent_width = self.parent.winfo_width()
                parent_height = self.parent.winfo_height()
                
                # 부모 창 중앙 계산
                x = parent_x + (parent_width - dialog_width) // 2
                y = parent_y + (parent_height - dialog_height) // 2
            except tk.TclError:
                # 부모 창 정보를 가져올 수 없는 경우 화면 중앙으로
                x = (screen_width - dialog_width) // 2
                y = (screen_height - dialog_height) // 2
            
            # 화면 경계 확인 및 조정
            margin = 20
            if x + dialog_width > screen_width - margin:
                x = screen_width - dialog_width - margin
            if x < margin:
                x = margin
            if y + dialog_height > screen_height - 60:  # 작업 표시줄 고려
                y = screen_height - dialog_height - 60
            if y < margin:
                y = margin
            
            self.dialog.geometry(f"+{x}+{y}")
            
            # 미리보기 업데이트
            self.update_preview()
            percent_combo.bind('<<ComboboxSelected>>', lambda e: self.update_preview())
            
            # 🔥 ESC 키 바인딩 추가
            self.dialog.bind('<Escape>', lambda e: self.cancel())
            
            logger.debug("영역확장 다이얼로그 생성 완료")
            
        except Exception as e:
            logger.error(f"다이얼로그 생성 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def extend_with_debug(self):
        """디버깅 포함된 확장 실행"""
        try:
            logger.debug("확장 버튼이 클릭되었습니다!")
            
            # 결과 설정
            self.result = {
                'direction': self.direction.get(),
                'percentage': self.percentage.get(),
                'bg_color': self.bg_color.get() if not self.transparent.get() else None,
                'transparent': self.transparent.get()
            }
            
            logger.debug(f"확장 설정: {self.result}")
            
            # 다이얼로그 닫기
            self.dialog.destroy()
            
        except Exception as e:
            logger.error(f"확장 실행 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def update_preview(self):
        """미리보기 업데이트 - 수정된 버전"""
        try:
            # 🔥 더 안전한 조건 검사
            if (not hasattr(self.app, 'feedback_items') or 
                not self.app.feedback_items or 
                not hasattr(self.app, 'current_index') or
                not (0 <= self.app.current_index < len(self.app.feedback_items))):
                self.preview_label.config(text="미리보기를 사용할 수 없습니다")
                return
            
            current_item = self.app.feedback_items[self.app.current_index]
            orig_width = current_item['image'].width
            orig_height = current_item['image'].height
            
            percentage = self.percentage.get()
            direction = self.direction.get()
            
            if direction in ['right', 'left']:
                add_width = int(orig_width * percentage / 100)
                new_size = f"{orig_width + add_width} x {orig_height}"
            else:  # up, down
                add_height = int(orig_height * percentage / 100)
                new_size = f"{orig_width} x {orig_height + add_height}"
            
            self.preview_label.config(text=f"새 크기: {new_size} 픽셀")
            
        except Exception as e:
            logger.debug(f"미리보기 업데이트 오류: {e}")
            self.preview_label.config(text="미리보기 오류")
    
    def choose_color(self):
        """배경색 선택"""
        try:
            color = colorchooser.askcolor(color=self.bg_color.get())
            if color[1]:
                self.bg_color.set(color[1])
                self.color_button.config(bg=color[1])
                self.transparent.set(False)
        except Exception as e:
            logger.debug(f"색상 선택 오류: {e}")
    
    def toggle_transparent(self):
        """투명 배경 토글"""
        if self.transparent.get():
            self.color_button.config(state='disabled')
        else:
            self.color_button.config(state='normal')
    
    def extend(self):
        """확장 실행 - 기존 메서드 유지"""
        self.extend_with_debug()
    
    def cancel(self):
        """취소"""
        logger.debug("취소 버튼이 클릭되었습니다!")
        self.result = None
        self.dialog.destroy()

class SmartCanvasViewer:
    """스마트 캔버스 뷰어 - 줌/팬 및 주석 기능 통합"""
    
    def __init__(self, parent, item, app_instance, item_index):
        self.parent = parent
        self.item = item
        self.app = app_instance
        self.item_index = item_index
        
        # 줌/팬 상태 (리스트박스 기반 시스템) 
        # 🔥 초기값은 setup_canvas_size에서 실제 크기에 맞게 설정됨
        self.zoom_level = 50  # 임시 기본값 (실제로는 setup_canvas_size에서 결정)
        self.current_zoom = 50  # 현재 줌 레벨
        self.min_zoom = 10   # 최소 10%
        self.max_zoom = 200  # 최대 200%로 제한
        self.pan_x = 0
        self.pan_y = 0
        
        # 줌 옵션 - 200%까지만
        self.zoom_options = [10, 20, 30, 50, 80, 100, 120, 150, 200]
        self.zoom_var = None
        
        # 팬 기능 비활성화
        
        # 캔버스 크기 계산
        self.setup_canvas_size()
        self.create_viewer()
        
    def setup_canvas_size(self):
        """캔버스 크기 설정 - 적절한 초기 크기로 시작"""
        orig_width = self.item['image'].width
        orig_height = self.item['image'].height
        
        # 🔥 base_canvas 크기는 원본 이미지와 동일하게 설정 (줌 비율 계산용)
        self.base_canvas_width = orig_width
        self.base_canvas_height = orig_height
        
        # 화면 크기 고려한 초기 캔버스 크기 설정 (너무 크지 않게)
        screen_width = self.app.root.winfo_screenwidth()
        screen_height = self.app.root.winfo_screenheight()
        
        # 🔥 캔버스 카드 이미지 크기 대폭 확대 - 화면 크기 제한 완화
        max_initial_width = int(screen_width * 1.2)  # 90% → 120%로 대폭 증가 (화면 넘어가도 OK)
        max_initial_height = int(screen_height * 1.0)  # 90% → 100%로 증가 (세로는 화면 크기까지)
        
        # 🔥 최소 표시 크기를 더 크게 설정 (이미지가 더 잘 보이도록)
        min_display_width = 400  # 최소 크기 대폭 확대 (200 → 400)
        min_display_height = 300  # 최소 크기 대폭 확대 (150 → 300)
        
        # 종횡비를 유지하면서 초기 크기 계산
        aspect_ratio = orig_height / orig_width
        
        if orig_width <= max_initial_width and orig_height <= max_initial_height:
            # 원본이 화면보다 작으면 그대로 사용
            self.canvas_width = orig_width
            self.canvas_height = orig_height
            self.display_ratio = 1.0
        else:
            # 원본이 크면 종횡비 유지하며 축소
            if aspect_ratio > max_initial_height / max_initial_width:
                # 세로가 긴 경우 - 세로 기준으로 조정
                self.canvas_height = max_initial_height
                self.canvas_width = int(max_initial_height / aspect_ratio)
            else:
                # 가로가 긴 경우 - 가로 기준으로 조정
                self.canvas_width = max_initial_width
                self.canvas_height = int(max_initial_width * aspect_ratio)
            
            # 🔥 최소 크기 보정 (너무 작아지면 최소 크기로 조정)
            if self.canvas_width < min_display_width or self.canvas_height < min_display_height:
                # 최소 크기 기준으로 다시 계산
                width_scale = min_display_width / orig_width
                height_scale = min_display_height / orig_height
                min_scale = max(width_scale, height_scale)  # 최소 크기를 보장하는 스케일
                
                self.canvas_width = int(orig_width * min_scale)
                self.canvas_height = int(orig_height * min_scale)
                logger.info(f"최소 크기 보정 적용: {self.canvas_width}x{self.canvas_height}")
            
            self.display_ratio = self.canvas_width / orig_width
        
        logger.info(f"초기 캔버스 크기: {self.canvas_width}x{self.canvas_height} (원본: {orig_width}x{orig_height}, 비율: {self.display_ratio:.3f})")
        
        # 웹툰 이미지 알림
        if aspect_ratio > 3.0:
            logger.info(f"세로 긴 이미지 감지: 비율 {aspect_ratio:.1f}:1")
        elif orig_width > 2000 or orig_height > 2000:
            logger.info(f"대형 이미지: {orig_width}x{orig_height}")
            
        # 🔥 줌 시스템은 초기 표시 크기에 맞게 설정
        # display_ratio에 따라 초기 줌 레벨 결정
        display_zoom_level = int(self.display_ratio * 100)
        self.zoom_level = display_zoom_level
        self.current_zoom = display_zoom_level
        
        logger.info(f"초기 줌 레벨: {display_zoom_level}% (화면 맞춤)")
        logger.info(f"100% 선택 시 원본 크기({orig_width}x{orig_height})로 확대됩니다")
        
    def create_viewer(self):
        """뷰어 생성"""
        # 메인 프레임
        self.main_frame = tk.Frame(self.parent, bg='white')
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 툴바 프레임
        toolbar_frame = tk.Frame(self.main_frame, bg='white', height=30)
        toolbar_frame.pack(fill=tk.X, padx=5, pady=2)
        toolbar_frame.pack_propagate(False)
        
        # 줌 컨트롤
        tk.Label(toolbar_frame, text="🔍", bg='white', font=('Arial', 12)).pack(side=tk.LEFT, padx=2)
        
        # 줌 비율 리스트박스
        zoom_control_frame = tk.Frame(toolbar_frame, bg='white')
        zoom_control_frame.pack(side=tk.LEFT, padx=5)
        
        tk.Label(zoom_control_frame, text="크기:", bg='white', fg='#666',
                font=('Arial', 8)).pack(side=tk.LEFT, padx=2)
        
        # 줌 변수 초기화 (실제 줌 레벨로 설정)
        self.zoom_var = tk.StringVar(value=f"{self.current_zoom}%")
        
        # 🔥 줌 변수 변경 감지를 위한 trace 추가
        self.zoom_var.trace('w', lambda *args: self.on_zoom_var_change(self.zoom_var.get()))
        
        # 콤보박스 스타일 프레임
        combo_frame = tk.Frame(zoom_control_frame, bg='white', relief='solid', bd=1)
        combo_frame.pack(side=tk.LEFT, padx=2)
        
        self.zoom_combobox = tk.OptionMenu(combo_frame, self.zoom_var,
                                          *[f"{opt}%" for opt in self.zoom_options],
                                          command=self.on_zoom_combobox_change)
        self.zoom_combobox.configure(bg='white', fg='#666', relief='flat', bd=0,
                                   highlightthickness=0, font=('Arial', 8),
                                   width=6, anchor='center')
        self.zoom_combobox['menu'].configure(bg='white', fg='#666', font=('Arial', 8))
        self.zoom_combobox.pack(padx=2, pady=1)
        
        # 줌 버튼들
        tk.Button(toolbar_frame, text="1:1", command=self.zoom_100,
                 font=('Arial', 8), relief='flat', bd=1,
                 bg='white', fg='#666', padx=8, pady=2).pack(side=tk.LEFT, padx=2)
        
        tk.Button(toolbar_frame, text="맞춤", command=self.zoom_fit,
                 font=('Arial', 8), relief='flat', bd=1,
                 bg='white', fg='#666', padx=8, pady=2).pack(side=tk.LEFT, padx=2)
        
        # 캔버스 프레임 - 스크롤 지원
        canvas_frame = tk.Frame(self.main_frame, bg='#e0e0e0')
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        
        # 🔥 스크롤 가능한 캔버스 컨테이너 생성
        # 캔버스 크기가 프레임보다 클 경우 스크롤바 자동 표시
        canvas_container = tk.Frame(canvas_frame, bg='#e0e0e0')
        canvas_container.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        
        # 캔버스 생성 - 진한 회색 테두리로 얇게 표시
        is_current = (self.item_index == self.app.current_index)
        # 🔥 진한 회색 테두리로 얇게 표시 (활성/비활성 구분 없음)
        border_color = '#888888'  # 진한 회색
        thickness = 1  # 얇은 두께
        
        # 🔥 캔버스 크기는 setup_canvas_size에서 이미 설정된 값 사용
        display_width = self.canvas_width
        display_height = self.canvas_height
        
        logger.info(f"캔버스 생성: {display_width}x{display_height} (base: {self.base_canvas_width}x{self.base_canvas_height})")
        
        self.canvas = tk.Canvas(canvas_container, 
                               width=display_width, 
                               height=display_height,
                               bg='#f5f5f5',
                               highlightthickness=thickness,
                               highlightbackground=border_color,
                               highlightcolor=border_color,
                               relief='flat', bd=1)
        self.canvas.pack(anchor='center', padx=4, pady=4)
        
        # actual_canvas 크기 설정
        self.actual_canvas_width = display_width
        self.actual_canvas_height = display_height
        
        # 🔥 줌 콤보박스 초기값 설정
        self.zoom_var.set(f"{self.current_zoom}%")
        
        logger.info(f"캔버스 생성 완료: {display_width}x{display_height} (줌: {self.current_zoom}%)")
        
        # 이미지 로드 및 표시
        self.load_and_display_image()
        
        # 이벤트 바인딩
        self.bind_events()
        
        # 활성 캔버스 목록에 추가
        if not hasattr(self.app, 'active_canvases'):
            self.app.active_canvases = []
        self.app.active_canvases.append(self.canvas)
        
    def load_and_display_image(self):
        """이미지 로드 및 표시 - 원본 해상도 유지"""
        orig_width = self.item['image'].width
        orig_height = self.item['image'].height
        
        # 🔥 캐시 키에 display_ratio 포함하여 해상도별 구분
        cache_key = f"{id(self.item['image'])}_{self.canvas_width}_{self.canvas_height}_{self.display_ratio:.3f}"
        
        if cache_key in self.app.image_cache:
            self.photo = self.app.image_cache[cache_key]
            logger.debug(f"이미지 캐시 히트: {cache_key}")
        else:
            display_image = self.item['image'].copy()
            
            # 🔥 display_ratio가 1.0인 경우 원본 크기 유지, 아닌 경우만 리사이즈
            if abs(self.display_ratio - 1.0) < 0.001:  # 거의 1.0인 경우 (부동소수점 오차 고려)
                # 원본 크기 그대로 사용
                logger.info(f"원본 해상도 유지: {orig_width}x{orig_height}")
                # 리사이즈 없이 그대로 사용
            else:
                # 캔버스 크기에 맞게 리사이즈
                display_image = display_image.resize((self.canvas_width, self.canvas_height), 
                                                    Image.Resampling.LANCZOS)
                logger.info(f"이미지 리사이즈: {orig_width}x{orig_height} → {self.canvas_width}x{self.canvas_height} (비율: {self.display_ratio:.3f})")
            
            # RGBA 이미지 처리
            if display_image.mode == 'RGBA':
                checker_bg = self.app.create_checker_background(display_image.width, display_image.height)
                final_image = Image.alpha_composite(checker_bg, display_image)
                self.photo = ImageTk.PhotoImage(final_image)
            else:
                self.photo = ImageTk.PhotoImage(display_image)
            
            # 캐시에 저장 (메모리 관리)
            if len(self.app.image_cache) > self.app.max_cache_size:
                # 오래된 캐시 항목 제거
                oldest_key = next(iter(self.app.image_cache))
                del self.app.image_cache[oldest_key]
                logger.debug(f"이미지 캐시 정리: {oldest_key}")
            
            self.app.image_cache[cache_key] = self.photo
        
        # 이미지 표시
        self.image_id = self.canvas.create_image(0, 0, image=self.photo, anchor='nw', tags='background')
        self.canvas.image = self.photo
        
        # 🔥 주석 그리기 시 스케일링 지원 메서드 사용
        actual_img_width = self.photo.width()
        actual_img_height = self.photo.height()
        self.draw_annotations_with_zoom(self.canvas, self.item, actual_img_width, actual_img_height)
        
        # 레이어 순서 설정
        self.canvas.tag_lower(self.image_id)
        self.canvas.tag_raise('annotation')
        
        logger.debug(f"이미지 표시 완료: 캔버스 {self.canvas_width}x{self.canvas_height}, 실제 이미지 {actual_img_width}x{actual_img_height}")
        
    def bind_events(self):
        """이벤트 바인딩 - 줌/팬 마우스 기능 제거, 스케일링 지원 주석 시스템"""
        # 🔥 스케일링 지원 주석 이벤트 직접 바인딩
        self.bind_smart_canvas_events()
        
        # 스크롤 이벤트 (페이지 스크롤용)
        self.canvas.bind('<MouseWheel>', self.on_mousewheel)
    
    def bind_smart_canvas_events(self):
        """스케일링을 지원하는 캔버스 이벤트 바인딩"""
        # 🔥 기존 바인딩 완전 제거
        self.canvas.unbind_all('<Button-1>')
        self.canvas.unbind('<Button-1>')
        self.canvas.unbind('<B1-Motion>')
        self.canvas.unbind('<ButtonRelease-1>')
        self.canvas.unbind('<Double-Button-1>')
        
        # 🔥 통합 마우스 이벤트 핸들러
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        self.canvas.bind('<B1-Motion>', self.on_canvas_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_canvas_release)
        self.canvas.bind('<Double-Button-1>', self.on_canvas_double_click)
        self.canvas.bind('<Motion>', self.on_mouse_motion)  # 🔥 마우스 움직임 이벤트 추가
        
        # 드로잉 상태 변수
        self.is_drawing = False
        self.start_x = 0
        self.start_y = 0
        self.current_x = 0
        self.current_y = 0
        self.temp_objects = []
        self.pen_points = []
        
        logger.debug(f"SmartCanvas 이벤트 바인딩 완료: {self.canvas}")
    
    def on_canvas_click(self, event):
        """캔버스 클릭 이벤트 - 스케일링 고려"""
        try:
            # 🔥 텍스트 도구인 경우 바로 텍스트 입력
            if self.app.current_tool == 'text':
                self.add_text_annotation_click(event.x, event.y)
                return
                
            # 🔥 선택 도구인 경우 선택 처리
            if self.app.current_tool == 'select':
                # 텍스트 주석 드래그 체크 먼저
                for annotation in self.item.get('annotations', []):
                    if annotation['type'] == 'text':
                        # 캔버스 좌표로 변환
                        text_x = annotation['x'] * (self.canvas_width / self.item['image'].width)
                        text_y = annotation['y'] * (self.canvas_height / self.item['image'].height)
                        text = annotation.get('text', '')
                        font_size = annotation.get('font_size', 14)
                        
                        # 텍스트 영역 계산 (anchor='nw' 기준으로 수정)
                        text_width = max(len(text) * font_size * 0.7, 60)
                        text_height = max(font_size * 1.5, 25)
                        margin = 15
                        # nw 앵커이므로 text_x, text_y가 왼쪽 상단 모서리
                        click_x1 = text_x - margin
                        click_y1 = text_y - margin
                        click_x2 = text_x + text_width + margin
                        click_y2 = text_y + text_height + margin
                        
                        # 마우스가 텍스트 영역 안에 있는지 확인
                        if (click_x1 <= event.x <= click_x2 and
                            click_y1 <= event.y <= click_y2):
                            self.app.dragging_text = annotation
                            self.app.drag_start_x = event.x
                            self.app.drag_start_y = event.y
                            self.app.original_text_x = annotation['x']
                            self.app.original_text_y = annotation['y']
                            # 🔥 드래그 상태 활성화 (중요!)
                            self.is_drawing = True
                            logger.debug(f"✅ SmartCanvas 텍스트 주석 드래그 시작: '{text}' at ({event.x}, {event.y})")
                            logger.debug(f"   텍스트 영역: ({click_x1:.1f}, {click_y1:.1f}) - ({click_x2:.1f}, {click_y2:.1f})")
                            return
                
                # 이미지 주석 드래그 체크
                for annotation in self.item.get('annotations', []):
                    if annotation['type'] == 'image':
                        # 캔버스 좌표로 변환
                        image_x = annotation['x'] * (self.canvas_width / self.item['image'].width)
                        image_y = annotation['y'] * (self.canvas_height / self.item['image'].height)
                        image_width = annotation['width'] * (self.canvas_width / self.item['image'].width)
                        image_height = annotation['height'] * (self.canvas_height / self.item['image'].height)
                        
                        # 클릭 영역을 약간 확장
                        margin = 5
                        click_x1 = image_x - margin
                        click_y1 = image_y - margin
                        click_x2 = image_x + image_width + margin
                        click_y2 = image_y + image_height + margin
                        
                        # 마우스가 이미지 영역 안에 있는지 확인
                        if (click_x1 <= event.x <= click_x2 and
                            click_y1 <= event.y <= click_y2):
                            self.app.dragging_image = annotation
                            self.app.drag_start_x = event.x
                            self.app.drag_start_y = event.y
                            self.app.original_image_x = annotation['x']
                            self.app.original_image_y = annotation['y']
                            # 🔥 드래그 상태 활성화 (중요!)
                            self.is_drawing = True
                            logger.debug(f"✅ SmartCanvas 이미지 주석 드래그 시작 at ({event.x}, {event.y})")
                            print(f"🖼️ SmartCanvas 이미지 주석 드래그 시작 - 위치: ({annotation['x']}, {annotation['y']})")
                            return
                
                # 텍스트 드래그가 아닌 경우 영역 선택 모드
                self.app.clear_selection()
                self.app.selection_start = (event.x, event.y)
                self.is_drawing = True  # 🔥 중요: 드래그 상태 활성화
                logger.debug("선택 도구 - 영역 선택 시작")
                return
            
            self.is_drawing = True
            self.start_x = event.x
            self.start_y = event.y
            self.current_x = event.x
            self.current_y = event.y
            
            # 펜 도구의 경우 점 수집 시작
            if self.app.current_tool == 'pen':
                self.pen_points = [(event.x, event.y)]
            
            logger.debug(f"SmartCanvas 클릭: ({event.x}, {event.y}), 도구: {self.app.current_tool}")
            
        except Exception as e:
            logger.debug(f"SmartCanvas 클릭 오류: {e}")
    
    def add_text_annotation_click(self, x, y):
        """텍스트 주석 추가 (클릭 시)"""
        try:
            # 큰 텍스트 입력 다이얼로그 사용
            text_input = self.app.show_custom_text_dialog()
            
            if text_input:
                if isinstance(text_input, dict):
                    # 새로운 형식: 폰트 설정 포함
                    text_content = text_input.get('text', '').strip()
                    font_size = text_input.get('font_size', self.app.font_size)
                    color = text_input.get('color', self.app.annotation_color)
                    bold = text_input.get('bold', False)
                    
                    if text_content:
                        self.add_text_annotation_with_style(x, y, text_content, font_size, color, bold)
                elif isinstance(text_input, str):
                    # 기존 형식: 문자열만
                    text_content = text_input.strip()
                    if text_content:
                        logger.debug(f"📝 SmartCanvas 텍스트 주석 추가 (기본): '{text_content}'")
                        self.add_text_annotation(x, y, text_content)
                
        except Exception as e:
            logger.error(f"SmartCanvas 텍스트 입력 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def on_canvas_drag(self, event):
        """캔버스 드래그 이벤트 - 스케일링 고려"""
        try:
            if not self.is_drawing:
                return
                
            # 🔥 선택 도구인 경우 드래그 처리
            if self.app.current_tool == 'select':
                # 텍스트 주석 드래그 처리
                if self.app.dragging_text:
                    # 이동 거리 계산 (캔버스 좌표계)
                    dx = event.x - self.app.drag_start_x
                    dy = event.y - self.app.drag_start_y
                    
                    # 이미지 좌표계로 변환
                    scale_x = self.item['image'].width / self.canvas_width
                    scale_y = self.item['image'].height / self.canvas_height
                    
                    # 새 위치 계산 (이미지 좌표계)
                    self.app.dragging_text['x'] = self.app.original_text_x + (dx * scale_x)
                    self.app.dragging_text['y'] = self.app.original_text_y + (dy * scale_y)
                    
                    # 화면 갱신
                    self.redraw_annotations()
                    logger.debug(f"🔄 SmartCanvas 텍스트 드래그 중: dx={dx}, dy={dy}, 새 위치=({self.app.dragging_text['x']:.1f}, {self.app.dragging_text['y']:.1f})")
                    return
                
                # 이미지 주석 드래그 처리
                if hasattr(self.app, 'dragging_image') and self.app.dragging_image:
                    # 이동 거리 계산 (캔버스 좌표계)
                    dx = event.x - self.app.drag_start_x
                    dy = event.y - self.app.drag_start_y
                    
                    # 이미지 좌표계로 변환
                    scale_x = self.item['image'].width / self.canvas_width
                    scale_y = self.item['image'].height / self.canvas_height
                    
                    # 새 위치 계산 (이미지 좌표계)
                    self.app.dragging_image['x'] = self.app.original_image_x + (dx * scale_x)
                    self.app.dragging_image['y'] = self.app.original_image_y + (dy * scale_y)
                    
                    # 화면 갱신
                    self.redraw_annotations()
                    logger.debug(f"🔄 SmartCanvas 이미지 드래그 중: dx={dx}, dy={dy}, 새 위치=({self.app.dragging_image['x']:.1f}, {self.app.dragging_image['y']:.1f})")
                    print(f"🖼️ SmartCanvas 이미지 드래그 중: dx={dx}, dy={dy}, 새 위치: ({self.app.dragging_image['x']:.1f}, {self.app.dragging_image['y']:.1f})")
                    return
                
                # 영역 선택 사각형 그리기
                if self.app.selection_start and self.is_drawing:
                    self.canvas.delete('selection_rect')
                    start_x, start_y = self.app.selection_start
                    
                    self.app.selection_rect = self.canvas.create_rectangle(
                        start_x, start_y, event.x, event.y,
                        outline='blue', width=2, dash=(5, 5), tags='selection_rect'
                    )
                    logger.debug(f"선택 영역 업데이트: ({start_x}, {start_y}) -> ({event.x}, {event.y})")
                return
                
            self.current_x = event.x
            self.current_y = event.y
            
            # 이전 임시 객체 삭제
            for obj in self.temp_objects:
                self.canvas.delete(obj)
            self.temp_objects.clear()
            
            if self.app.current_tool == 'pen':
                # 펜 도구: 점 추가 및 실시간 라인 그리기
                self.pen_points.append((event.x, event.y))
                if len(self.pen_points) >= 2:
                    temp_obj = self.canvas.create_line(
                        self.pen_points, 
                        fill=self.app.annotation_color,
                        width=self.app.line_width,
                        smooth=True,
                        tags='temp'
                    )
                    self.temp_objects.append(temp_obj)
                    
            elif self.app.current_tool == 'arrow':
                # 🔥 화살표: 라인 + 화살표 머리
                temp_obj = self.canvas.create_line(
                    self.start_x, self.start_y, self.current_x, self.current_y,
                    fill=self.app.annotation_color,
                    width=self.app.line_width,
                    tags='temp'
                )
                self.temp_objects.append(temp_obj)
                
                # 🔥 개선된 화살표 머리 그리기 (임시 미리보기용)
                if abs(self.current_x - self.start_x) > 5 or abs(self.current_y - self.start_y) > 5:
                    # 임시 화살표 머리를 위한 간단한 삼각형
                    arrow_length = math.sqrt((self.current_x - self.start_x)**2 + (self.current_y - self.start_y)**2)
                    base_arrow_size = max(8, self.app.line_width * 2.5)
                    max_arrow_size = arrow_length * 0.3
                    arrow_size = min(base_arrow_size, max_arrow_size)
                    arrow_size = max(arrow_size, 6)
                    
                    angle = math.atan2(self.current_y - self.start_y, self.current_x - self.start_x)
                    angle_offset = math.pi / 8 if arrow_size < 12 else math.pi / 6
                    
                    # 🔥 돌출된 삼각형 끝점 계산
                    extend_distance = arrow_size * 0.15
                    tip_x = self.current_x + extend_distance * math.cos(angle)
                    tip_y = self.current_y + extend_distance * math.sin(angle)
                    
                    # 화살표 머리 좌표 계산 (원래 끝점 기준)
                    wing1_x = self.current_x - arrow_size * math.cos(angle - angle_offset)
                    wing1_y = self.current_y - arrow_size * math.sin(angle - angle_offset)
                    wing2_x = self.current_x - arrow_size * math.cos(angle + angle_offset)
                    wing2_y = self.current_y - arrow_size * math.sin(angle + angle_offset)
                    
                    # 🔥 뾰족하고 돌출된 삼각형 임시 미리보기
                    temp_arrow_head = self.canvas.create_polygon(
                        tip_x, tip_y,      # 더 앞으로 돌출된 끝점
                        wing1_x, wing1_y,  # 왼쪽 날개
                        wing2_x, wing2_y,  # 오른쪽 날개
                        fill=self.app.annotation_color,
                        outline=self.app.annotation_color,
                        tags='temp'
                    )
                    self.temp_objects.append(temp_arrow_head)
                    
            elif self.app.current_tool == 'line':
                # 라인: 시작점에서 현재점까지 직선
                temp_obj = self.canvas.create_line(
                    self.start_x, self.start_y, self.current_x, self.current_y,
                    fill=self.app.annotation_color,
                    width=self.app.line_width,
                    tags='temp'
                )
                self.temp_objects.append(temp_obj)
                
            elif self.app.current_tool in ['oval', 'rect']:
                # 도형: 시작점과 현재점으로 사각형/원
                if self.app.current_tool == 'oval':
                    temp_obj = self.canvas.create_oval(
                        self.start_x, self.start_y, self.current_x, self.current_y,
                        outline=self.app.annotation_color,
                        width=self.app.line_width,
                        tags='temp'
                    )
                else:
                    temp_obj = self.canvas.create_rectangle(
                        self.start_x, self.start_y, self.current_x, self.current_y,
                        outline=self.app.annotation_color,
                        width=self.app.line_width,
                        tags='temp'
                    )
                self.temp_objects.append(temp_obj)
                
        except Exception as e:
            logger.debug(f"SmartCanvas 드래그 오류: {e}")
    
    def on_canvas_release(self, event):
        """캔버스 릴리즈 이벤트 - 스케일링 고려하여 주석 저장"""
        try:
            if not self.is_drawing:
                return
                
            # 🔥 선택 도구인 경우 선택 완료 처리
            if self.app.current_tool == 'select':
                # 텍스트 주석 드래그 종료
                if self.app.dragging_text:
                    # 상태 저장 (실제 이동이 있었을 경우에만)
                    if (self.app.dragging_text['x'] != self.app.original_text_x or 
                        self.app.dragging_text['y'] != self.app.original_text_y):
                        self.app.undo_manager.save_state(self.item['id'], self.item['annotations'])
                        logger.debug("✅ SmartCanvas 텍스트 주석 이동 완료 - 상태 저장됨")
                        self.app.update_status_message("📝 텍스트 주석이 이동되었습니다", 2000)
                    else:
                        logger.debug("📍 SmartCanvas 텍스트 위치 변경 없음")
                    
                    # 드래그 상태 완전 초기화
                    self.app.dragging_text = None
                    self.app.drag_start_x = None
                    self.app.drag_start_y = None
                    self.app.original_text_x = None
                    self.app.original_text_y = None
                    self.is_drawing = False  # 🔥 드래그 상태 종료
                    return
                
                # 이미지 주석 드래그 종료
                if hasattr(self.app, 'dragging_image') and self.app.dragging_image:
                    # 상태 저장 (실제 이동이 있었을 경우에만)
                    if (self.app.dragging_image['x'] != self.app.original_image_x or 
                        self.app.dragging_image['y'] != self.app.original_image_y):
                        self.app.undo_manager.save_state(self.item['id'], self.item['annotations'])
                        logger.debug("✅ SmartCanvas 이미지 주석 이동 완료 - 상태 저장됨")
                        print(f"🖼️ SmartCanvas 이미지 주석 이동 완료 - 최종 위치: ({self.app.dragging_image['x']:.1f}, {self.app.dragging_image['y']:.1f})")
                        self.app.update_status_message("🖼️ 이미지 주석이 이동되었습니다", 2000)
                    else:
                        logger.debug("📍 SmartCanvas 이미지 위치 변경 없음")
                    
                    # 드래그 상태 완전 초기화
                    self.app.dragging_image = None
                    self.app.drag_start_x = None
                    self.app.drag_start_y = None
                    self.app.original_image_x = None
                    self.app.original_image_y = None
                    self.is_drawing = False  # 🔥 드래그 상태 종료
                    return
                
                # 영역 선택 완료
                if self.app.selection_start and self.is_drawing:
                    start_x, start_y = self.app.selection_start
                    end_x, end_y = event.x, event.y
                    
                    # 선택 영역이 충분히 큰 경우에만 처리
                    if abs(end_x - start_x) > 10 and abs(end_y - start_y) > 10:
                        selected_indices = self.get_annotations_in_selection(start_x, start_y, end_x, end_y)
                        
                        if selected_indices:
                            # 선택된 주석들 저장
                            self.app.selected_annotations = [self.item['annotations'][i] for i in selected_indices]
                            # 선택된 주석들 하이라이트
                            self.highlight_selected_annotations()
                            self.app.update_status_message(f"{len(selected_indices)}개 주석이 선택되었습니다")
                            logger.debug(f"주석 선택 완료: {len(selected_indices)}개")
                        else:
                            self.app.update_status_message("선택 영역에 주석이 없습니다")
                            logger.debug("선택 영역에 주석 없음")
                    
                    # 선택 사각형 제거
                    self.canvas.delete('selection_rect')
                    self.app.selection_rect = None
                    self.app.selection_start = None
                
                # 🔥 중요: 드래그 상태 종료
                self.is_drawing = False
                return
                
            # 임시 객체 삭제
            for obj in self.temp_objects:
                self.canvas.delete(obj)
            self.temp_objects.clear()
            
            self.is_drawing = False
            
            # 🔥 스케일링을 고려한 주석 추가
            self.add_smart_annotation(event)
            
        except Exception as e:
            logger.debug(f"SmartCanvas 릴리즈 오류: {e}")
    
    def on_canvas_double_click(self, event):
        """더블클릭으로 주석 편집 또는 텍스트 주석 추가"""
        try:
            if self.app.current_tool == 'select':
                # 선택 도구인 경우 주석 편집 시도
                for annotation in self.item.get('annotations', []):
                    if annotation['type'] == 'image':
                        # 이미지 주석 더블클릭 체크
                        image_x = annotation['x'] * (self.canvas_width / self.item['image'].width)
                        image_y = annotation['y'] * (self.canvas_height / self.item['image'].height)
                        image_width = annotation['width'] * (self.canvas_width / self.item['image'].width)
                        image_height = annotation['height'] * (self.canvas_height / self.item['image'].height)
                        
                        if (image_x <= event.x <= image_x + image_width and
                            image_y <= event.y <= image_y + image_height):
                            self.app.edit_annotation_image(annotation)
                            return
                    
                    elif annotation['type'] == 'text':
                        # 텍스트 주석 더블클릭 체크
                        text_x = annotation['x'] * (self.canvas_width / self.item['image'].width)
                        text_y = annotation['y'] * (self.canvas_height / self.item['image'].height)
                        text = annotation.get('text', '')
                        font_size = annotation.get('font_size', 14)
                        
                        text_width = max(len(text) * font_size * 0.7, 60)
                        text_height = max(font_size * 1.5, 25)
                        
                        if (text_x <= event.x <= text_x + text_width and
                            text_y <= event.y <= text_y + text_height):
                            new_text = self.app.show_custom_text_dialog()
                            if new_text is not None:
                                annotation['text'] = new_text
                                self.app.refresh_current_item()
                            return
                
                logger.debug("선택 도구 - 빈 공간 더블클릭, 편집할 주석 없음")
                return
                
            # 다른 도구인 경우 큰 텍스트 입력 다이얼로그 사용
            text = self.app.show_custom_text_dialog()
            if text:
                self.add_text_annotation(event.x, event.y, text)
                
        except Exception as e:
            logger.debug(f"SmartCanvas 더블클릭 오류: {e}")
    
    def add_smart_annotation(self, event):
        """스케일링을 고려한 주석 추가"""
        try:
            # 🔥 캔버스 좌표를 원본 이미지 좌표로 변환
            orig_width = self.item['image'].width
            orig_height = self.item['image'].height
            
            # 현재 표시된 이미지 크기
            display_width = self.canvas_width
            display_height = self.canvas_height
            
            # 스케일 팩터 (캔버스 -> 원본)
            scale_x = orig_width / display_width
            scale_y = orig_height / display_height
            
            if self.app.current_tool == 'pen':
                if len(self.pen_points) >= 2:
                    # 펜 포인트들을 원본 좌표로 변환
                    orig_points = [(x * scale_x, y * scale_y) for x, y in self.pen_points]
                    
                    annotation = {
                        'type': 'pen',
                        'points': orig_points,
                        'color': self.app.annotation_color,
                        'width': self.app.line_width
                    }
                    self.item['annotations'].append(annotation)
                    logger.debug(f"SmartCanvas 펜 주석 추가: {len(orig_points)}개 점")
                    
            elif self.app.current_tool in ['arrow', 'line']:
                if abs(self.current_x - self.start_x) >= 5 or abs(self.current_y - self.start_y) >= 5:
                    annotation = {
                        'type': self.app.current_tool,
                        'start_x': self.start_x * scale_x,
                        'start_y': self.start_y * scale_y,
                        'end_x': self.current_x * scale_x,
                        'end_y': self.current_y * scale_y,
                        'color': self.app.annotation_color,
                        'width': self.app.line_width
                    }
                    self.item['annotations'].append(annotation)
                    logger.debug(f"SmartCanvas {self.app.current_tool} 주석 추가")
                    
            elif self.app.current_tool in ['oval', 'rect']:
                if abs(self.current_x - self.start_x) >= 5 and abs(self.current_y - self.start_y) >= 5:
                    annotation = {
                        'type': self.app.current_tool,
                        'x1': self.start_x * scale_x,
                        'y1': self.start_y * scale_y,
                        'x2': self.current_x * scale_x,
                        'y2': self.current_y * scale_y,
                        'color': self.app.annotation_color,
                        'width': self.app.line_width
                    }
                    self.item['annotations'].append(annotation)
                    logger.debug(f"SmartCanvas {self.app.current_tool} 주석 추가")
            
            # 주석 다시 그리기
            self.redraw_annotations()
            
            # Undo 상태 저장
            self.app.undo_manager.save_state(self.item['id'], self.item['annotations'])
            
        except Exception as e:
            logger.debug(f"SmartCanvas 주석 추가 오류: {e}")
    
    def add_text_annotation(self, x, y, text):
        """텍스트 주석 추가 (기본)"""
        return self.add_text_annotation_with_style(x, y, text, self.app.font_size, self.app.annotation_color)
    
    def add_text_annotation_with_style(self, x, y, text, font_size, color, bold=False):
        """텍스트 주석 추가 (스타일 포함)"""
        try:
            # 🔥 캔버스 좌표를 원본 이미지 좌표로 변환
            orig_width = self.item['image'].width
            orig_height = self.item['image'].height
            
            scale_x = orig_width / self.canvas_width
            scale_y = orig_height / self.canvas_height
            
            annotation = {
                'type': 'text',
                'x': x * scale_x,
                'y': y * scale_y,
                'text': text,
                'color': color,
                'font_size': font_size,
                'bold': bold
            }
            
            # Undo 상태 저장 (추가 전에)
            self.app.undo_manager.save_state(self.item['id'], self.item['annotations'])
            
            self.item['annotations'].append(annotation)
            
            # 주석 다시 그리기
            self.redraw_annotations()
            
            # 상태 메시지 업데이트 (볼드 정보 포함)
            style_info = "볼드" if bold else "일반"
            self.app.update_status_message(f"텍스트 주석이 추가되었습니다: '{text}' ({font_size}px, {style_info})", 3000)
            
            return True
            
        except Exception as e:
            logger.error(f"SmartCanvas 텍스트 주석 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def redraw_annotations(self):
        """주석 다시 그리기 - 스케일링 적용"""
        try:
            # 기존 주석 삭제
            self.canvas.delete('annotation')
            
            # 새로운 주석 그리기
            self.draw_annotations_with_zoom(self.canvas, self.item, self.canvas_width, self.canvas_height)
            
            # 레이어 순서 재설정
            self.canvas.tag_lower('background')
            self.canvas.tag_raise('annotation')
            
        except Exception as e:
            logger.debug(f"SmartCanvas 주석 재그리기 오류: {e}")
    
    def on_zoom_var_change(self, value):
        """줌 변수 변경 감지 (trace 콜백)"""
        try:
            logger.debug(f"줌 변수 변경 감지: {value}")
            # "100%" 형태에서 숫자만 추출
            zoom_percent = int(value.replace('%', ''))
            if zoom_percent != self.zoom_level:  # 실제로 변경된 경우만 처리
                logger.info(f"줌 레벨 변경: {self.zoom_level}% → {zoom_percent}%")
                self.zoom_level = zoom_percent
                self.update_zoom()
        except Exception as e:
            logger.error(f"줌 변수 변경 감지 오류: {e}")
        
    def on_zoom_combobox_change(self, value):
        """콤보박스로 줌 변경"""
        try:
            logger.debug(f"줌 콤보박스 변경: {value}")
            # "100%" 형태에서 숫자만 추출
            zoom_percent = int(value.replace('%', ''))
            logger.info(f"줌 레벨 변경: {self.zoom_level}% → {zoom_percent}%")
            self.zoom_level = zoom_percent
            self.update_zoom()
        except Exception as e:
            logger.error(f"줌 콤보박스 변경 오류: {e}")
            # 폴백으로 현재 값 유지
    

    
    def set_zoom_level(self, zoom_percent):
        """줌 레벨 설정"""
        try:
            logger.debug(f"📐 줌 레벨 설정 요청: {zoom_percent}%")
            # 가장 가까운 옵션으로 조정
            closest_option = min(self.zoom_options, key=lambda x: abs(x - zoom_percent))
            old_zoom = self.zoom_level
            self.zoom_level = closest_option
            self.zoom_var.set(f"{self.zoom_level}%")
            logger.info(f"📐 줌 레벨 설정: {old_zoom}% → {self.zoom_level}% (요청: {zoom_percent}%)")
            self.update_zoom()
        except Exception as e:
            logger.error(f"❌ 줌 레벨 설정 오류: {e}")
            
    def zoom_100(self):
        """100% 크기"""
        logger.info("🎯 1:1 버튼 클릭 - 100% 줌 설정")
        self.set_zoom_level(100)
        
    def zoom_fit(self):
        """화면에 맞춤 (웹툰 지원 개선)"""
        try:
            # 🔥 현재 컨테이너 크기 확인 - 여러 방법으로 시도
            container_width = self.canvas.winfo_width()
            container_height = self.canvas.winfo_height()
            
            # 캔버스 크기가 유효하지 않으면 부모 컨테이너 크기 사용
            if container_width <= 10 or container_height <= 10:
                try:
                    parent_width = self.canvas.master.winfo_width()
                    parent_height = self.canvas.master.winfo_height()
                    if parent_width > 10 and parent_height > 10:
                        container_width = parent_width - 100  # 여백 고려
                        container_height = parent_height - 100
                        logger.debug(f"부모 컨테이너 크기 사용: {container_width}x{container_height}")
                except:
                    # 폴백: 기본 크기 사용
                    container_width = 800
                    container_height = 600
                    logger.debug("기본 컨테이너 크기 사용: 800x600")
            
            if container_width > 10 and container_height > 10:  # 유효한 크기인 경우
                orig_width = self.item['image'].width
                orig_height = self.item['image'].height
                
                # 웹툰 감지
                aspect_ratio = orig_height / orig_width
                is_webtoon = aspect_ratio > 2.5
                
                if is_webtoon:
                    # 🔥 웹툰의 경우 가로 기준으로 맞춤 (세로는 스크롤로 해결)
                    width_ratio = (container_width - 40) / orig_width * 100  # 충분한 여백
                    fit_zoom = min(width_ratio, 100)  # 100% 이하로 제한
                    logger.info(f"웹툰 맞춤 줌: {fit_zoom:.1f}% (가로 기준)")
                else:
                    # 일반 이미지는 기존 로직
                    width_ratio = (container_width - 20) / orig_width * 100
                    height_ratio = (container_height - 20) / orig_height * 100
                    fit_zoom = min(width_ratio, height_ratio)
                    logger.info(f"일반 맞춤 줌: {fit_zoom:.1f}%")
                
                # 가장 가까운 옵션 선택
                self.set_zoom_level(int(fit_zoom))
            else:
                # 기본값으로 설정
                logger.debug("컨테이너 크기 확인 불가 - 기본값 사용")
                self.set_zoom_level(50)  # 웹툰을 고려하여 더 작은 기본값
        except Exception as e:
            logger.debug(f"맞춤 줌 오류: {e}")
            self.set_zoom_level(50)
        
    def update_zoom(self):
        """줌 업데이트 - base_canvas 크기 기준으로 한 상대적 줌"""
        try:
            logger.info(f"🔍 줌 업데이트 시작: {self.zoom_level}%")
            
            # 줌 레벨 저장
            self.current_zoom = self.zoom_level
            
            # 🔥 base_canvas 크기 확인 (초기화되지 않은 경우 설정)
            if not hasattr(self, 'base_canvas_width') or not hasattr(self, 'base_canvas_height'):
                logger.warning("base_canvas 크기가 설정되지 않음 - 기본값으로 설정")
                self.base_canvas_width = self.item['image'].width
                self.base_canvas_height = self.item['image'].height
            
            # 🔥 줌 비율을 base_canvas 크기에 적용
            zoom_ratio = self.zoom_level / 100.0
            new_width = int(self.base_canvas_width * zoom_ratio)
            new_height = int(self.base_canvas_height * zoom_ratio)
            
            logger.debug(f"기본 크기: {self.base_canvas_width}x{self.base_canvas_height}")
            logger.debug(f"줌 {self.zoom_level}% 적용: {new_width}x{new_height} (비율: {zoom_ratio})")
            
            # 🔥 최소 크기 제한 (종횡비 유지)
            if new_width < 50 or new_height < 50:  # 최소 크기 축소 (100 → 50)
                min_scale = max(50 / self.base_canvas_width, 50 / self.base_canvas_height)
                new_width = int(self.base_canvas_width * min_scale)
                new_height = int(self.base_canvas_height * min_scale)
                logger.debug(f"최소 크기 제한 적용: {new_width}x{new_height}")
            
            # 🔥 최대 크기 제한 (종횡비 유지, 대폭 증가)
            max_size = 30000  # 최대 크기 증가 (15000 → 30000)
            if new_width > max_size or new_height > max_size:
                max_scale = min(max_size / self.base_canvas_width, max_size / self.base_canvas_height)
                new_width = int(self.base_canvas_width * max_scale)
                new_height = int(self.base_canvas_height * max_scale)
                logger.debug(f"최대 크기 제한 적용: {new_width}x{new_height}")
            
            # 캔버스 크기 업데이트
            old_canvas_width = self.canvas_width
            old_canvas_height = self.canvas_height
            self.canvas_width = new_width
            self.canvas_height = new_height
            logger.info(f"📏 캔버스 크기 변경: {old_canvas_width}x{old_canvas_height} → {new_width}x{new_height}")
            
            # 실제 캔버스 위젯 크기 변경
            logger.debug("캔버스 위젯 크기 변경 시도...")
            self.canvas.configure(width=new_width, height=new_height)
            logger.debug("✓ 캔버스 위젯 크기 변경 완료")
            
            # 이미지 다시 그리기
            logger.debug("이미지 리드로우 시작...")
            self.redraw_with_zoom()
            logger.debug("✓ 이미지 리드로우 완료")
            
            logger.info(f"🎯 줌 업데이트 성공: {self.zoom_level}% → {new_width}x{new_height} (기준: {self.base_canvas_width}x{self.base_canvas_height})")
            
        except Exception as e:
            logger.error(f"❌ 줌 업데이트 오류: {e}")
            import traceback
            logger.error(f"스택 트레이스: {traceback.format_exc()}")
        
    def redraw_with_zoom(self):
        """새로운 크기로 이미지 및 주석 다시 그리기"""
        try:
            logger.debug("🎨 이미지 리드로우 시작")
            
            # 기존 이미지 삭제
            self.canvas.delete('background')
            self.canvas.delete('annotation')
            logger.debug("기존 이미지/주석 삭제 완료")
            
            # 현재 캔버스 크기 (이미 줌 비율 적용됨)
            display_width = self.canvas_width
            display_height = self.canvas_height
            logger.debug(f"표시 크기: {display_width}x{display_height}")
            
            if display_width > 0 and display_height > 0:
                # 이미지 리사이즈
                logger.debug("이미지 리사이즈 시작...")
                display_image = self.item['image'].copy()
                display_image = display_image.resize((display_width, display_height), 
                                                   Image.Resampling.LANCZOS)
                logger.debug(f"✓ 이미지 리사이즈 완료: {display_width}x{display_height}")
                
                # RGBA 이미지 처리
                if display_image.mode == 'RGBA':
                    checker_bg = self.app.create_checker_background(display_width, display_height)
                    final_image = Image.alpha_composite(checker_bg, display_image)
                    self.photo = ImageTk.PhotoImage(final_image)
                    logger.debug("✓ RGBA 이미지 처리 완료")
                else:
                    self.photo = ImageTk.PhotoImage(display_image)
                    logger.debug("✓ RGB 이미지 처리 완료")
                
                # 이미지 표시 (팬 적용)
                x = self.pan_x if hasattr(self, 'pan_x') else 0
                y = self.pan_y if hasattr(self, 'pan_y') else 0
                
                self.image_id = self.canvas.create_image(x, y, image=self.photo, 
                                                       anchor='nw', tags='background')
                self.canvas.image = self.photo
                logger.debug(f"✓ 캔버스에 이미지 표시 완료: 위치({x}, {y})")
                
                # 🔥 주석 다시 그리기 시작
                logger.debug("주석 다시 그리기 시작...")
                self.draw_annotations_with_zoom(self.canvas, self.item, display_width, display_height)
                logger.debug("✓ 주석 다시 그리기 완료")
                
                # 레이어 순서
                self.canvas.tag_lower(self.image_id)
                self.canvas.tag_raise('annotation')
                
                logger.info(f"🎨 이미지 리드로우 성공: {display_width}x{display_height}, 줌레벨: {self.zoom_level}%")
                
        except Exception as e:
            logger.debug(f"줌 다시 그리기 오류: {e}")
    
    def draw_annotations_with_zoom(self, canvas, item, canvas_width, canvas_height):
        """줌 레벨을 고려한 주석 그리기"""
        try:
            if not item or not canvas_width or not canvas_height:
                return
            
            # 원본 이미지 크기
            orig_width = item['image'].width
            orig_height = item['image'].height
            
            # 🔥 스케일 팩터 계산 - 원본 크기 대비 현재 표시 크기 비율
            # 주의: 올바른 종횡비 유지를 위해 원본 크기를 기준으로 계산
            scale_x = canvas_width / orig_width
            scale_y = canvas_height / orig_height
            
            # 🔥 종횡비 체크 - 차이가 5% 이상이면 경고
            if abs(scale_x - scale_y) / max(scale_x, scale_y) > 0.05:
                logger.warning(f"종횡비 불일치 감지: X축({scale_x:.3f}) vs Y축({scale_y:.3f})")
            
            logger.debug(f"주석 스케일링: 원본({orig_width}x{orig_height}) -> 표시({canvas_width}x{canvas_height}), 스케일({scale_x:.2f}, {scale_y:.2f})")
            
            for annotation in item['annotations']:
                try:
                    ann_type = annotation['type']
                    if ann_type == 'arrow':
                        x1 = annotation['start_x'] * scale_x
                        y1 = annotation['start_y'] * scale_y
                        x2 = annotation['end_x'] * scale_x
                        y2 = annotation['end_y'] * scale_y
                        color = annotation['color']
                        width = max(1, int(annotation['width'] * min(scale_x, scale_y)))  # 선 굵기도 스케일링
                        # 🔥 개선된 화살표 그리기 사용
                        create_improved_arrow(canvas, x1, y1, x2, y2, color, width, 'annotation')
                    elif ann_type == 'line':
                        x1 = annotation['start_x'] * scale_x
                        y1 = annotation['start_y'] * scale_y
                        x2 = annotation['end_x'] * scale_x
                        y2 = annotation['end_y'] * scale_y
                        color = annotation['color']
                        width = max(1, int(annotation['width'] * min(scale_x, scale_y)))  # 선 굵기도 스케일링
                        canvas.create_line(x1, y1, x2, y2, fill=color, width=width, tags='annotation')
                    elif ann_type == 'pen':
                        points = annotation.get('points', [])
                        if points:
                            scaled_points = [(x * scale_x, y * scale_y) for x, y in points]
                            color = annotation['color']
                            width = max(1, int(annotation['width'] * min(scale_x, scale_y)))  # 선 굵기도 스케일링
                            canvas.create_line(scaled_points, fill=color, width=width, tags='annotation', smooth=True)
                    elif ann_type in ['oval', 'rect']:
                        x1 = annotation['x1'] * scale_x
                        y1 = annotation['y1'] * scale_y
                        x2 = annotation['x2'] * scale_x
                        y2 = annotation['y2'] * scale_y
                        color = annotation['color']
                        width = max(1, int(annotation['width'] * min(scale_x, scale_y)))  # 선 굵기도 스케일링
                        if ann_type == 'oval':
                            canvas.create_oval(x1, y1, x2, y2, outline=color, width=width, tags='annotation')
                        else:
                            canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=width, tags='annotation')
                    
                    elif ann_type == 'text':
                        x = annotation['x'] * scale_x
                        y = annotation['y'] * scale_y
                        text = annotation.get('text', '')
                        font_size = max(8, int(annotation.get('font_size', 14) * min(scale_x, scale_y)))  # 폰트 크기도 스케일링
                        color = annotation['color']
                        bold = annotation.get('bold', False)  # 볼드 정보
                        
                        try:
                            # 🔥 안정적인 한글 폰트 사용 - 볼드 지원
                            font_name = self.app.font_manager.ui_font[0] if hasattr(self.app, 'font_manager') else '맑은 고딕'
                            font_weight = "bold" if bold else "normal"
                            font_tuple = (font_name, font_size, font_weight)
                            canvas.create_text(x, y, text=text, font=font_tuple, fill=color, tags='annotation', anchor='nw')
                        except Exception as e:
                            # 폴백: 기본 폰트 사용
                            try:
                                font_tuple = (font_name, font_size)
                                canvas.create_text(x, y, text=text, font=font_tuple, fill=color, tags='annotation', anchor='nw')
                            except:
                                canvas.create_text(x, y, text=text, fill=color, tags='annotation', anchor='nw')
                    
                    elif ann_type == 'image':
                        x = annotation['x'] * scale_x
                        y = annotation['y'] * scale_y
                        width = annotation['width'] * scale_x
                        height = annotation['height'] * scale_y
                        
                        try:
                            # base64 이미지 디코딩
                            image_data = base64.b64decode(annotation['image_data'])
                            image = Image.open(io.BytesIO(image_data))
                            
                            # 반전 처리
                            if annotation.get('flip_horizontal', False):
                                image = image.transpose(Image.FLIP_LEFT_RIGHT)
                            if annotation.get('flip_vertical', False):
                                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                            
                            # 회전 처리 (크기 유지 개선)
                            rotation = annotation.get('rotation', 0)
                            if rotation != 0:
                                try:
                                    # 이미지를 RGBA 모드로 변환하여 투명도 지원
                                    if image.mode != 'RGBA':
                                        image = image.convert('RGBA')
                                    
                                    # 원본 크기 저장
                                    original_size = image.size
                                    
                                    # 투명 배경으로 회전 (expand=True로 잘림 방지)
                                    rotated_image = image.rotate(-rotation, expand=True, fillcolor=(0, 0, 0, 0))
                                    
                                    # 회전 후 크기와 원본 크기 비율 계산
                                    scale_factor = min(
                                        original_size[0] / rotated_image.size[0],
                                        original_size[1] / rotated_image.size[1]
                                    )
                                    
                                    # 회전된 이미지를 원본 크기에 맞게 조정
                                    if scale_factor < 1.0:
                                        # 회전으로 인해 크기가 커진 경우, 원본 크기에 맞게 스케일 다운
                                        temp_size = (
                                            int(rotated_image.size[0] * scale_factor),
                                            int(rotated_image.size[1] * scale_factor)
                                        )
                                        scaled_image = rotated_image.resize(temp_size, Image.Resampling.LANCZOS)
                                        
                                        # 원본 크기 캔버스에 중앙 배치
                                        image = Image.new('RGBA', original_size, (0, 0, 0, 0))
                                        paste_x = (original_size[0] - scaled_image.size[0]) // 2
                                        paste_y = (original_size[1] - scaled_image.size[1]) // 2
                                        image.paste(scaled_image, (paste_x, paste_y), scaled_image)
                                    else:
                                        # 회전 후에도 원본 크기보다 작은 경우, 중앙에 배치
                                        image = Image.new('RGBA', original_size, (0, 0, 0, 0))
                                        paste_x = (original_size[0] - rotated_image.size[0]) // 2
                                        paste_y = (original_size[1] - rotated_image.size[1]) // 2
                                        image.paste(rotated_image, (paste_x, paste_y), rotated_image)
                                    
                                    logger.debug(f"이미지 회전 완료 (크기 유지): {rotation}도, 원본={original_size}, 최종={image.size}")
                                    
                                except Exception as e:
                                    logger.error(f"이미지 회전 오류: {e}")
                                    # 폴백: 기본 회전
                                image = image.rotate(-rotation, expand=True)
                            
                            # 크기 조정 (이제 회전 후에도 원본 비율 유지됨)
                            display_image = image.resize((int(width), int(height)), Image.Resampling.LANCZOS)
                            
                            # 투명도 처리
                            opacity = annotation.get('opacity', 100) / 100.0
                            if opacity < 1.0:
                                # RGBA 모드로 변환
                                if display_image.mode != 'RGBA':
                                    display_image = display_image.convert('RGBA')
                                # 투명도 적용
                                alpha = display_image.split()[-1]
                                alpha = alpha.point(lambda p: p * opacity)
                                display_image.putalpha(alpha)
                            
                            # 🔥 아웃라인 처리 (ImageDraw로 완전한 테두리)
                            if annotation.get('outline', False):
                                from PIL import ImageDraw
                                
                                # 아웃라인을 위한 이미지 확장
                                outline_width = annotation.get('outline_width', 3)
                                new_size = (display_image.width + outline_width * 2, 
                                           display_image.height + outline_width * 2)
                                outlined_image = Image.new('RGBA', new_size, (0, 0, 0, 0))
                                
                                # 🔥 ImageDraw로 확실한 흰색 아웃라인 그리기 (투명도 100% 안전)
                                draw = ImageDraw.Draw(outlined_image)
                                for i in range(outline_width):
                                    # 바깥쪽부터 안쪽까지 여러 겹의 흰색 테두리
                                    draw.rectangle([
                                        i, i, 
                                        outlined_image.width - 1 - i, 
                                        outlined_image.height - 1 - i
                                    ], outline=(255, 255, 255, 255), width=1)
                                
                                # 원본 이미지를 중앙에 붙이기 (RGBA 마스크 사용)
                                outlined_image.paste(display_image, (outline_width, outline_width), display_image if display_image.mode == 'RGBA' else None)
                                
                                display_image = outlined_image
                                x -= outline_width
                                y -= outline_width
                            
                            # tkinter용 이미지로 변환
                            photo = ImageTk.PhotoImage(display_image)
                            
                            # 캔버스에 그리기
                            image_id = canvas.create_image(x, y, image=photo, anchor='nw', tags='annotation image_annotation')
                            
                            # 이미지 참조 유지 (가비지 컬렉션 방지)
                            if not hasattr(canvas, 'annotation_images'):
                                canvas.annotation_images = {}
                            canvas.annotation_images[image_id] = photo
                            
                            # 이미지 주석을 최상단으로 올리기
                            canvas.tag_raise(image_id)
                            
                        except Exception as e:
                            logger.debug(f"이미지 주석 스케일링 그리기 오류: {e}")
                except Exception as e:
                    logger.debug(f"개별 주석 스케일링 오류: {e}")
            
            logger.debug(f"스케일링된 주석 그리기 완료: {len(item['annotations'])}개")
            
        except Exception as e:
            logger.debug(f"주석 스케일링 그리기 전체 오류: {e}")
    

            
    def get_annotations_in_selection(self, x1, y1, x2, y2):
        """선택 영역 안의 주석들 찾기"""
        try:
            selected_indices = []
            
            # 영역 정규화
            min_x, max_x = min(x1, x2), max(x1, x2)
            min_y, max_y = min(y1, y2), max(y1, y2)
            
            # 실제 이미지 좌표로 변환
            scale_x = self.item['image'].width / self.canvas_width
            scale_y = self.item['image'].height / self.canvas_height
            
            real_min_x = min_x * scale_x
            real_max_x = max_x * scale_x
            real_min_y = min_y * scale_y
            real_max_y = max_y * scale_y
            
            for i, annotation in enumerate(self.item.get('annotations', [])):
                if self.app.annotation_in_rect(annotation, real_min_x, real_min_y, real_max_x, real_max_y):
                    selected_indices.append(i)
            
            return selected_indices
            
        except Exception as e:
            logger.debug(f"주석 선택 영역 검사 오류: {e}")
            return []

    def highlight_selected_annotations(self):
        """선택된 주석들 하이라이트"""
        try:
            # 기존 하이라이트 제거
            self.canvas.delete('highlight')
            if not self.app.selected_annotations:
                return
                
            scale_x = self.canvas_width / self.item['image'].width
            scale_y = self.canvas_height / self.item['image'].height
            
            # 선택된 각 주석에 대해 하이라이트 그리기
            for annotation in self.app.selected_annotations:
                try:
                    ann_type = annotation['type']
                    if ann_type == 'arrow':
                        x1 = annotation['start_x'] * scale_x
                        y1 = annotation['start_y'] * scale_y
                        x2 = annotation['end_x'] * scale_x
                        y2 = annotation['end_y'] * scale_y
                        # 화살표 주변에 하이라이트 박스
                        margin = 10
                        self.canvas.create_rectangle(
                            min(x1, x2) - margin, min(y1, y2) - margin,
                            max(x1, x2) + margin, max(y1, y2) + margin,
                            outline='lime', width=3, dash=(3, 3), tags='highlight'
                        )
                    elif ann_type == 'line':
                        x1 = annotation['start_x'] * scale_x
                        y1 = annotation['start_y'] * scale_y
                        x2 = annotation['end_x'] * scale_x
                        y2 = annotation['end_y'] * scale_y
                        # 라인 주변에 하이라이트 박스
                        margin = 10
                        self.canvas.create_rectangle(
                            min(x1, x2) - margin, min(y1, y2) - margin,
                            max(x1, x2) + margin, max(y1, y2) + margin,
                            outline='lime', width=3, dash=(3, 3), tags='highlight'
                        )
                    elif ann_type in ['oval', 'rect']:
                        x1 = annotation['x1'] * scale_x
                        y1 = annotation['y1'] * scale_y
                        x2 = annotation['x2'] * scale_x
                        y2 = annotation['y2'] * scale_y
                        # 도형 주변에 하이라이트 박스
                        margin = 10
                        self.canvas.create_rectangle(
                            min(x1, x2) - margin, min(y1, y2) - margin,
                            max(x1, x2) + margin, max(y1, y2) + margin,
                            outline='lime', width=3, dash=(3, 3), tags='highlight'
                        )
                    elif ann_type == 'text':
                        x = annotation['x'] * scale_x
                        y = annotation['y'] * scale_y
                        text = annotation.get('text', '')
                        font_size = annotation.get('font_size', 14)
                        # 텍스트 주변에 하이라이트 박스 (anchor='nw' 기준)
                        text_width = max(len(text) * font_size * 0.7, 60)
                        text_height = max(font_size * 1.5, 25)
                        self.canvas.create_rectangle(
                            x - 5, y - 5, x + text_width + 5, y + text_height + 5,
                            outline='lime', width=3, dash=(3, 3), tags='highlight'
                        )
                    elif ann_type == 'pen':
                        # 펜 경로의 바운딩 박스 계산
                        points = annotation.get('points', [])
                        if points:
                            xs = [p[0] * scale_x for p in points]
                            ys = [p[1] * scale_y for p in points]
                            margin = 10
                            self.canvas.create_rectangle(
                                min(xs) - margin, min(ys) - margin,
                                max(xs) + margin, max(ys) + margin,
                                outline='lime', width=3, dash=(3, 3), tags='highlight'
                            )
                    elif ann_type == 'image':
                        x = annotation['x'] * scale_x
                        y = annotation['y'] * scale_y
                        width = annotation['width'] * scale_x
                        height = annotation['height'] * scale_y
                        margin = 5
                        self.canvas.create_rectangle(
                            x - margin, y - margin,
                            x + width + margin, y + height + margin,
                            outline='lime', width=3, dash=(3, 3), tags='highlight'
                        )
                except Exception as e:
                    logger.debug(f"주석 하이라이트 오류: {e}")
        except Exception as e:
            logger.debug(f"하이라이트 처리 오류: {e}")

    def on_mouse_motion(self, event):
        """마우스 움직임 처리 - 텍스트 주석 hover 효과"""
        try:
            # 도구별 기본 커서 설정
            cursor_map = {
                'select': 'crosshair',      # 선택: 십자 커서
                'arrow': 'arrow',           # 화살표: 화살표 커서  
                'pen': 'target',            # 펜: 동그라미 커서
                'line': 'crosshair',        # 라인: 십자 커서
                'oval': 'crosshair',        # 원형: 십자 커서
                'rect': 'crosshair',        # 사각형: 십자 커서
                'text': 'crosshair'         # 텍스트: 십자 커서
            }
            
            default_cursor = cursor_map.get(self.app.current_tool, 'crosshair')
            
            # 선택 도구일 때만 주석 hover 효과 적용
            if self.app.current_tool == 'select':
                # 드래그 가능한 주석 위에 마우스가 있는지 확인
                over_draggable = False
                for annotation in self.item.get('annotations', []):
                    if annotation['type'] == 'text':
                        text_x = annotation['x'] * (self.canvas_width / self.item['image'].width)
                        text_y = annotation['y'] * (self.canvas_height / self.item['image'].height)
                        text = annotation.get('text', '')
                        font_size = annotation.get('font_size', 14)
                        
                        # 확장된 클릭 영역 계산 (anchor='nw' 기준)
                        text_width = max(len(text) * font_size * 0.7, 60)
                        text_height = max(font_size * 1.5, 25)
                        margin = 15
                        # nw 앵커이므로 text_x, text_y가 왼쪽 상단 모서리
                        click_x1 = text_x - margin
                        click_y1 = text_y - margin
                        click_x2 = text_x + text_width + margin
                        click_y2 = text_y + text_height + margin
                        
                        if (click_x1 <= event.x <= click_x2 and
                            click_y1 <= event.y <= click_y2):
                            over_draggable = True
                            break
                    
                    elif annotation['type'] == 'image':
                        # 이미지 주석 호버 감지
                        image_x = annotation['x'] * (self.canvas_width / self.item['image'].width)
                        image_y = annotation['y'] * (self.canvas_height / self.item['image'].height)
                        image_width = annotation['width'] * (self.canvas_width / self.item['image'].width)
                        image_height = annotation['height'] * (self.canvas_height / self.item['image'].height)
                        
                        # 클릭 영역을 약간 확장
                        margin = 5
                        click_x1 = image_x - margin
                        click_y1 = image_y - margin
                        click_x2 = image_x + image_width + margin
                        click_y2 = image_y + image_height + margin
                        
                        if (click_x1 <= event.x <= click_x2 and
                            click_y1 <= event.y <= click_y2):
                            over_draggable = True
                            break
                
                # 드래그 가능한 주석 위에 있으면 손가락 커서, 아니면 기본 커서
                if over_draggable:
                    self.canvas.configure(cursor='hand2')
                else:
                    self.canvas.configure(cursor=default_cursor)
            else:
                # 다른 도구들은 해당 도구의 커서 사용
                self.canvas.configure(cursor=default_cursor)
                    
        except Exception as e:
            pass  # hover 효과는 오류가 나도 계속 동작해야 함

    def on_mousewheel(self, event):
        """마우스 휠 스크롤"""
        # Ctrl이 눌리지 않은 경우에만 페이지 스크롤
        if not (event.state & 0x4):  # Ctrl 키가 눌리지 않음
            delta = int(-1 * (event.delta / 120)) if event.delta else 0
            self.app.main_canvas.yview_scroll(delta, 'units')
            return "break"

class FeedbackCanvasTool:
    def __init__(self, root):
        self.root = root
        
        # 기본 설정
        self.root.title(f"피드백 캔버스 V{VERSION}")
        self.root.geometry("1280x800")
        self.root.minsize(800, 600)
        
        # 시스템 모니터링
        self.system_monitor = SystemMonitor()
        
        # 폰트 매니저
        self.font_manager = OptimizedFontManager()
        
        # 통일된 버튼 스타일 정의
        self.button_styles = {
            'primary': {
                'bg': 'white', 'fg': '#2196F3',
                'relief': 'solid', 'bd': 1,
                'activebackground': '#e3f2fd',
                'activeforeground': '#2196F3'
            },
            'secondary': {
                'bg': 'white', 'fg': '#666666',
                'relief': 'solid', 'bd': 1,
                'activebackground': '#f5f5f5',
                'activeforeground': '#666666'
            },
            'success': {
                'bg': 'white', 'fg': '#4CAF50',
                'relief': 'solid', 'bd': 1,
                'activebackground': '#e8f5e8',
                'activeforeground': '#4CAF50'
            },
            'danger': {
                'bg': 'white', 'fg': '#f44336',
                'relief': 'solid', 'bd': 1,
                'activebackground': '#ffebee',
                'activeforeground': '#f44336'
            },
            'warning': {
                'bg': 'white', 'fg': '#FF9800',
                'relief': 'solid', 'bd': 1,
                'activebackground': '#fff3e0',
                'activeforeground': '#FF9800'
            },
            'info': {
                'bg': 'white', 'fg': '#17a2b8',
                'relief': 'solid', 'bd': 1,
                'activebackground': '#e0f7fa',
                'activeforeground': '#17a2b8'
            }
        }
        
        # 작업 관리자
        self.task_manager = AsyncTaskManager(root)
        self.thread_executor = SafeThreadExecutor()
        
        # PDF 생성기
        self.pdf_generator = HighQualityPDFGenerator(self.font_manager, self)
        
        # 실행 취소 관리자
        self.undo_manager = SmartUndoManager()
        
        # GitHub 업데이트 체커
        if GITHUB_UPDATE_AVAILABLE:
            self.update_checker = GitHubUpdateChecker()
            logger.info("✓ GitHub 업데이트 체커 초기화 완료")
        else:
            self.update_checker = None
            logger.warning("GitHub 업데이트 체커 사용 불가")
        
        # 피드백 항목 관리
        self.feedback_items = []
        self.current_index = -1
        self.selected_annotations = []
        self.last_selected_annotation = None
        
        # 주석 도구 설정
        self.current_tool = 'arrow'
        self.annotation_color = '#ff0000'
        self.line_width = 6
        self.font_size = 14
        
        # 드래그 관련 변수
        self.dragging_text = None
        self.dragging_image = None
        self.drag_start_x = None
        self.drag_start_y = None
        self.original_text_x = None
        self.original_text_y = None
        self.original_image_x = None
        self.original_image_y = None
        
        # 선택 영역 관련
        self.selection_rect = None
        self.selection_start = None
        self.drag_start = None
        
        # 활성 캔버스 목록
        self.active_canvases = []
        
        # 네비게이션 바
        self.navigation_bar = None
        
        # 프로젝트 정보
        self.project_title = tk.StringVar(value="")
        self.project_to = tk.StringVar(value="")
        self.project_from = tk.StringVar(value="")
        self.project_description = tk.StringVar(value="")
        self.project_footer = tk.StringVar(value="")
        self.footer_first_page_only = tk.BooleanVar(value=False)  # 꼬리말 첫 장만 출력
        
        # 🔥 PDF 페이지 크기 모드 설정 (기본값: A4)
        self.pdf_page_mode = 'A4'
        
        # 🔥 첫장 제외하기 옵션 (기본값: False)
        self.skip_title_page = False
        
        # UI 설정
        self.show_index_numbers = tk.BooleanVar(value=True)
        self.show_name = tk.BooleanVar(value=True)
        self.show_timestamp = tk.BooleanVar(value=True)
        self.auto_save_interval = tk.IntVar(value=10)
        self.pen_smoothing_strength = tk.IntVar(value=3)
        self.pen_smoothing_enabled = tk.BooleanVar(value=False)  # 🔥 손떨림 방지 기본값을 체크 해제로 변경
        self.show_creation_date = tk.BooleanVar(value=True)
        
        # 새로운 설정 옵션 추가
        self.pdf_quality = tk.IntVar(value=300)  # PDF DPI 설정 (기본 300)
        self.canvas_width = tk.IntVar(value=1000)  # 캔버스 기본 너비
        self.canvas_height = tk.IntVar(value=800)  # 캔버스 기본 높이
        
        # 설정 불러오기
        self.load_settings()
        
        # 성능 관련
        self.active_canvases = weakref.WeakSet()
        self.image_cache = weakref.WeakValueDictionary()
        self.max_cache_size = 12
        self._ui_update_scheduled = False
        self._last_memory_check = time.time()
        
        # 파일 처리 관련
        # 🔥 이미지 크기 제한 완화 - 더 큰 이미지 지원
        self.max_image_size = (4096, 8192)  # 4K 및 웹툰 이미지 지원
        self.optimize_images = False  # 기본적으로 원본 크기 유지
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
        
        # UI 구성
        self.setup_ui()
        
        # 하단 저작권 표시
        self.add_copyright_footer()
        
        # 키보드 단축키 바인딩
        self.setup_keyboard_shortcuts()
        
        # 자동 저장 설정
        self.setup_auto_save()
        
        # 메모리 모니터링 설정
        self.setup_memory_monitoring()
        
        # 종료 처리
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 🔥 아이콘 설정 추가
        self._setup_icon()
        
        # 시작 시 업데이트 확인 (비동기)
        self.schedule_update_check()
        
        logger.info("✓ 피드백 캔버스 초기화 완료")
    
    def _setup_icon(self):
        """아이콘 설정 - 간단한 방법"""
        print("[메인 창] 아이콘 설정 중...")
        setup_window_icon(self.root)

    def setup_auto_save(self):
        """자동 저장 설정"""
        def auto_save():
            try:
                if self.feedback_items:
                    temp_dir = Path(tempfile.gettempdir()) / "AkeoStudio_Feedback"
                    temp_dir.mkdir(exist_ok=True)

                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    auto_save_file = temp_dir / f"auto_save_{ts}.json"
                    
                    self.task_manager.submit_task(
                        self.save_project_to_file,
                        args=(auto_save_file,),
                        kwargs={'show_popup': False}, 
                        callback=lambda _: logger.info(f"자동 저장 완료: {auto_save_file}"),
                        error_callback=lambda e: logger.debug(f"자동 저장 실패: {e}")
                    )
            except Exception as e:
                logger.debug(f"자동 저장 오류: {e}")
            finally:
                interval_ms = self.auto_save_interval.get() * 60 * 1000
                self.root.after(interval_ms, auto_save)

        initial_ms = self.auto_save_interval.get() * 60 * 1000
        self.root.after(initial_ms, auto_save)

    def setup_memory_monitoring(self):
        """메모리 모니터링 설정"""
        def check_memory():
            try:
                current_time = time.time()
                if current_time - self._last_memory_check > 30:
                    self._last_memory_check = current_time
                    
                    if not self.system_monitor.check_memory_limit():
                        logger.warning("메모리 사용량 초과 - 자동 정리 실행")
                        self.cleanup_memory(force=True)
                        gc.collect()
                    
                    memory_mb = self.system_monitor.get_memory_usage()
                    if memory_mb > 0:
                        logger.debug(f"메모리 사용량: {memory_mb:.1f}MB")
                
            except Exception as e:
                logger.debug(f"메모리 모니터링 오류: {e}")
            
            self.root.after(30000, check_memory)
        
        self.root.after(30000, check_memory)

    def validate_image_file(self, file_path):
        """이미지 파일 유효성 검사"""
        try:
            path = Path(file_path)
            
            if path.suffix.lower() not in self.supported_formats:
                return False, f"지원하지 않는 파일 형식입니다: {path.suffix}"
            
            file_size = path.stat().st_size
            if file_size > 100 * 1024 * 1024:
                return False, "파일 크기가 너무 큽니다 (100MB 제한)"
            
            with Image.open(file_path) as img:
                img.verify()
            
            return True, "OK"
            
        except Exception as e:
            return False, f"이미지 파일을 읽을 수 없습니다: {str(e)}"

    def optimize_image(self, image):
        """이미지 최적화 - 웹툰 지원 강화"""
        try:
            original_size = image.size
            width, height = image.size
            aspect_ratio = height / width
            
            # 🔥 웹툰 감지 및 메모리 효율성 고려
            is_webtoon = aspect_ratio > 2.5
            current_memory = self.system_monitor.get_memory_usage()
            
            # 메모리 사용량이 높은 경우 더 적극적인 최적화
            memory_pressure = current_memory > 2000  # 2GB 이상
            
            if is_webtoon:
                logger.info(f"웹툰 이미지 감지: {width}x{height} (비율: {aspect_ratio:.1f}:1)")
                
                # 웹툰의 경우 더 큰 해상도 허용하되, 메모리 압박 시 조정
                if memory_pressure:
                    max_pixels = 8000 * 8000  # 메모리 압박 시 제한
                    logger.warning(f"메모리 압박 감지 ({current_memory:.1f}MB) - 웹툰 최적화 적용")
                else:
                    max_pixels = 12000 * 12000  # 일반적인 경우 더 큰 허용
            else:
                # 일반 이미지
                max_pixels = 8000 * 8000 if not memory_pressure else 6000 * 6000
            
            # 크기 최적화 실행
            original_pixels = width * height
            if original_pixels > max_pixels:
                ratio = math.sqrt(max_pixels / original_pixels)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                
                # 최소 해상도 보장
                min_width = 800 if is_webtoon else 600
                min_height = 1200 if is_webtoon else 600
                
                if new_width < min_width or new_height < min_height:
                    scale_x = min_width / width if width > min_width else 1.0
                    scale_y = min_height / height if height > min_height else 1.0
                    scale = min(scale_x, scale_y, 1.0)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"이미지 최적화: {original_size} → {image.size} ({'웹툰' if is_webtoon else '일반'})")
            else:
                logger.debug(f"이미지 최적화 생략: {original_size} ({'웹툰' if is_webtoon else '일반'})")
            
            # 🔥 필수적인 색상 모드 변환만 수행
            if image.mode == 'RGBA':
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[-1] if 'A' in image.mode else None)
                image = rgb_image
            elif image.mode not in ['RGB', 'L']:
                image = image.convert('RGB')
            
            return image
            
        except Exception as e:
            logger.error(f"이미지 최적화 오류: {e}")
            return image

    def setup_keyboard_shortcuts(self):
        """키보드 단축키 설정"""
        try:
            shortcuts = {
                '<Control-z>': self.handle_undo,
                '<Control-Z>': self.handle_undo,
                '<Control-s>': lambda e: self.save_project(),
                '<Control-S>': lambda e: self.save_project(),
                '<Control-o>': lambda e: self.load_project(),
                '<Control-O>': lambda e: self.load_project(),
                '<Control-e>': lambda e: self.show_pdf_info_dialog(),
                '<Control-E>': lambda e: self.show_pdf_info_dialog(),
                '<Control-Shift-E>': lambda e: self.export_to_excel_async(),
                '<Control-Shift-e>': lambda e: self.export_to_excel_async(),
                '<Delete>': lambda e: self.handle_delete_key(),
                '<BackSpace>': lambda e: self.handle_delete_key(),
                '<F1>': lambda e: self.show_help(),
                '<F5>': lambda e: self.refresh_ui(),
                '<Escape>': lambda e: self.handle_escape_key(),
                '<Control-q>': lambda e: self.capture_area_async(),
                '<Control-Q>': lambda e: self.capture_area_async(),
                '<Control-w>': lambda e: self.capture_fullscreen_async(),
                '<Control-W>': lambda e: self.capture_fullscreen_async(),
                '<Control-n>': lambda e: self.create_blank_canvas(),
                '<Control-N>': lambda e: self.create_blank_canvas(),
                '<Control-1>': lambda e: self.set_tool('select'),
                '<Control-2>': lambda e: self.set_tool('arrow'),
                '<Control-3>': lambda e: self.set_tool('line'),
                '<Control-4>': lambda e: self.set_tool('pen'),
                '<Control-5>': lambda e: self.set_tool('oval'),
                '<Control-6>': lambda e: self.set_tool('rect'),
                '<Control-7>': lambda e: self.set_tool('text'),
            }
            
            for key, func in shortcuts.items():
                self.root.bind(key, func)
            
            logger.info("✓ 키보드 단축키 설정 완료")
            
        except Exception as e:
            logger.error(f"키보드 단축키 설정 오류: {e}")
    
    def handle_delete_key(self):
        """Delete/BackSpace 키 처리"""
        try:
            if not self.feedback_items:
                self.update_status_message("삭제할 항목이 없습니다")
                return
            
            if not (0 <= self.current_index < len(self.feedback_items)):
                self.update_status_message("유효하지 않은 항목입니다")
                return

            # 선택된 주석이 있는 경우 - 주석만 삭제
            if self.selected_annotations:
                self.delete_selected_annotations()
                return

            # 선택된 주석이 없는 경우 - 아무 동작 하지 않음
            self.update_status_message("선택된 주석이 없습니다")
            
        except Exception as e:
            logger.error(f"삭제 처리 중 오류 발생: {e}")
            self.update_status_message("삭제 처리 중 오류가 발생했습니다")

    def handle_escape_key(self):
        """Escape 키 처리"""
        if self.selected_annotations:
            self.clear_selection()
            self.refresh_current_item()
        else:
            self.set_tool('arrow')

    def distance_to_line(self, px, py, x1, y1, x2, y2):
        """점에서 선분까지의 거리 계산"""
        try:
            A = px - x1
            B = py - y1
            C = x2 - x1
            D = y2 - y1
            
            dot = A * C + B * D
            len_sq = C * C + D * D
            
            if len_sq == 0:
                return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
            
            param = dot / len_sq
            
            if param < 0:
                xx, yy = x1, y1
            elif param > 1:
                xx, yy = x2, y2
            else:
                xx = x1 + param * C
                yy = y1 + param * D
            
            return ((px - xx) ** 2 + (py - yy) ** 2) ** 0.5
        except:
            return float('inf')

    def show_help(self):
        """도움말 표시"""
        # 이미 도움말 창이 열려있다면 포커스만 이동
        if hasattr(self, 'help_window') and self.help_window and self.help_window.winfo_exists():
            self.help_window.focus_force()
            return
            
        help_text = f"""🚀 피드백 캔버스 V{VERSION}

📌 주요 기능:
• 💾 저장/불러오기: 프로젝트 저장 및 불러오기
• 📄 PDF 내보내기: 고품질 PDF 문서 생성 (300 DPI)
• 📊 Excel 내보내기: 피드백 목록 엑셀 파일 생성

🛠️ 주석 도구:
• 🔰 선택: 드래그로 영역 선택하여 다중 주석 선택/이동/삭제
• ➜ 화살표: 화살표 그리기
• ✏️ 펜: 자유 그리기 (손떨림 방지 지원)
• ⭕ 동그라미: 원형 그리기
• ⬜ 네모: 사각형 그리기
• 📝 텍스트: 텍스트 입력

⌨️ 단축키:
• Ctrl+Q: 영역선택 캡처
• Ctrl+W: 전체화면 캡처
• Ctrl+N: 빈 캔버스 생성
• Ctrl+Z: 되돌리기
• Ctrl+S: 저장
• Ctrl+O: 불러오기
• Ctrl+E: PDF 정보창 및 생성
• Ctrl+Shift+E: Excel 내보내기
• Ctrl+1~6: 도구 빠른 선택
• Delete/BackSpace: 선택된 주석 삭제
• Esc: 선택 해제 또는 화살표 도구
• F1: 도움말
• F5: 화면 새로고침

🔰 영역 선택 도구 사용법:
1. 선택 도구 클릭
2. 드래그로 사각형 영역 그리기
3. 영역 안의 모든 주석이 선택됨 (초록색 하이라이트)
4. 선택된 주석들을 드래그하여 이동
5. Delete/BackSpace로 선택된 주석들 일괄 삭제
6. Esc로 선택 해제

🎨 빈 캔버스 생성:
• 바탕색 선택 가능
• 기본 크기로 생성
• 주석 도구로 자유롭게 작업

💾 자동 저장:
• 간격: 옵션에서 설정 가능 (기본 5분)
• 파일명: autosave_날짜_시간.json
• 복구: 프로그램 시작 시 자동 감지

💡 사용법:
1. 화면 캡처, 이미지 업로드 또는 빈 캔버스 생성
2. 주석 도구로 피드백 표시
3. 피드백 텍스트 입력
4. PDF 또는 Excel로 내보내기

⚡ V1.6 새로운 기능:
• 🆕 영역 드래그로 다중 주석 선택
• 🆕 빈 캔버스 생성 기능
• 🆕 PDF 정보 입력창 분리
• 🔥 PDF 텍스트 주석 완벽 출력
• 🔥 UI 레이아웃 최적화
• 🐛 모든 기능 안정성 강화"""

        # 도움말 창 생성
        self.help_window = tk.Toplevel(self.root)
        self.help_window.title("도움말")
        
        # 🔥 아이콘 설정
        setup_window_icon(self.help_window)
        
        # 🔥 화면 해상도에 따른 적응형 크기 설정
        screen_width = self.help_window.winfo_screenwidth()
        screen_height = self.help_window.winfo_screenheight()
        
        # 기본 크기 계산 (화면 크기의 45% 너비, 80% 높이, 최소/최대 제한)
        dialog_width = max(600, min(900, int(screen_width * 0.45)))
        dialog_height = max(650, min(1000, int(screen_height * 0.8)))
        
        self.help_window.geometry(f"{dialog_width}x{dialog_height}")
        self.help_window.resizable(True, True)  # 🔥 크기 조정 가능
        self.help_window.minsize(500, 550)      # 🔥 최소 크기 설정
        self.help_window.maxsize(int(screen_width * 0.7), int(screen_height * 0.9))  # 🔥 최대 크기 설정
        self.help_window.transient(self.root)  # 메인 창의 자식 창으로 설정
        self.help_window.grab_set()  # 모달 창으로 설정
        
        # 스크롤 가능한 텍스트 영역
        frame = ttk.Frame(self.help_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text = tk.Text(frame, wrap=tk.WORD, font=self.font_manager.ui_font)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.insert(tk.END, help_text)
        text.configure(state=tk.DISABLED)
        
        # 하단 닫기 버튼
        button_frame = ttk.Frame(self.help_window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        close_button = ttk.Button(button_frame, text="닫기", command=self.help_window.destroy)
        close_button.pack(side=tk.RIGHT)
        
        # 창 닫기 이벤트 처리
        self.help_window.protocol("WM_DELETE_WINDOW", self.help_window.destroy)
        
        # 🔥 스마트 창 위치 조정 - 화면 경계 고려
        self.help_window.update_idletasks()
        dialog_width = self.help_window.winfo_width()
        dialog_height = self.help_window.winfo_height()
        screen_width = self.help_window.winfo_screenwidth()
        screen_height = self.help_window.winfo_screenheight()
        
        try:
            parent_x = self.root.winfo_x()
            parent_y = self.root.winfo_y()
            parent_width = self.root.winfo_width()
            parent_height = self.root.winfo_height()
            
            # 부모 창 중앙 계산
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2
        except tk.TclError:
            # 부모 창 정보를 가져올 수 없는 경우 화면 중앙으로
            x = (screen_width - dialog_width) // 2
            y = (screen_height - dialog_height) // 2
        
        # 화면 경계 확인 및 조정
        margin = 20
        if x + dialog_width > screen_width - margin:
            x = screen_width - dialog_width - margin
        if x < margin:
            x = margin
        if y + dialog_height > screen_height - 60:  # 작업 표시줄 고려
            y = screen_height - dialog_height - 60
        if y < margin:
            y = margin
        
        self.help_window.geometry(f"+{x}+{y}")

    def handle_undo(self, event=None):
        """되돌리기 처리"""
        try:
            if not self.feedback_items or not (0 <= self.current_index < len(self.feedback_items)):
                self.update_status_message("되돌릴 항목이 없습니다")
                return
            
            current_item = self.feedback_items[self.current_index]
            item_id = current_item['id']
            
            if self.undo_manager.can_undo(item_id):
                restored_annotations = self.undo_manager.undo(item_id)
                if restored_annotations is not None:
                    current_item['annotations'] = restored_annotations
                    self.clear_selection()  # 선택 해제
                    self.refresh_current_item()
                    
                    undo_count = len(restored_annotations)
                    self.update_status_message(f"되돌리기 완료 - 현재 {undo_count}개 주석")
            else:
                self.update_status_message("더 이상 되돌릴 수 없습니다")
            
        except Exception as e:
            logger.error(f"되돌리기 처리 오류: {e}")
            self.update_status_message("되돌리기 오류 발생")

    def update_status_message(self, message, duration=3000):
        """상태 메시지 업데이트"""
        try:
            if hasattr(self, 'status_label'):
                self.status_label.config(text=message)
                self.root.after(duration, self.update_status)
        except Exception as e:
            logger.debug(f"상태 메시지 업데이트 오류: {e}")
    
    def update_status(self):
        """상태 표시 업데이트"""
        try:
            if self.feedback_items and 0 <= self.current_index < len(self.feedback_items):
                current_name = self.feedback_items[self.current_index]['name']
                memory_usage = self.system_monitor.get_memory_usage()
                status_text = f"현재: {current_name} ({self.current_index + 1}/{len(self.feedback_items)}) | 메모리: {memory_usage:.1f}MB"
            else:
                status_text = "피드백을 추가하세요"
            
            if hasattr(self, 'status_label'):
                self.status_label.config(text=status_text)
            
            # 🔥 카드 테두리 업데이트 (네비게이션에서 선택 시 활성 상태 표시)
            self.update_card_borders()
            
            # 네비게이션 바 업데이트
            if self.navigation_bar:
                self.navigation_bar.refresh_minimap()
                
        except Exception as e:
            logger.debug(f"상태 업데이트 오류: {e}")

    def refresh_current_item(self):
        """현재 선택된 항목만 새로고침 - 강화된 버전"""
        try:
            if not self.feedback_items or not (0 <= self.current_index < len(self.feedback_items)):
                logger.debug("새로고침할 항목이 없거나 인덱스가 유효하지 않음")
                return
            
            current_item = self.feedback_items[self.current_index]
            logger.debug(f"현재 항목 새로고침: {current_item['name']}, 이미지 크기: {current_item['image'].size}")
            
            # 현재 아이템의 카드 찾기 및 업데이트
            refreshed = False
            for widget in self.scrollable_frame.winfo_children():
                if hasattr(widget, 'item_index') and widget.item_index == self.current_index:
                    # 해당 카드의 캔버스 찾기
                    for child in widget.winfo_children():
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, tk.Canvas):
                                # 캔버스 크기 재조정 및 이미지 재설정
                                self.update_canvas_size_and_image(grandchild, current_item)
                                self.redraw_canvas_annotations(grandchild, self.current_index)
                                refreshed = True
                                break
                    if refreshed:
                        break
            
            # 카드를 찾지 못했거나 새로고침이 필요한 경우 전체 UI 새로고침
            if not refreshed:
                logger.debug("카드를 찾지 못함 - 전체 UI 새로고침")
                self.schedule_ui_refresh()
            
        except Exception as e:
            logger.error(f"현재 항목 새로고침 오류: {e}")
            self.schedule_ui_refresh()

    def schedule_ui_refresh(self):
        """UI 새로고침 스케줄링"""
        if not self._ui_update_scheduled:
            self._ui_update_scheduled = True
            self.root.after_idle(self._perform_ui_refresh)

    def _perform_ui_refresh(self):
        """실제 UI 새로고침 수행"""
        try:
            self.refresh_ui()
        finally:
            self._ui_update_scheduled = False

    def update_canvas_size_and_image(self, canvas, item):
        """캔버스 크기와 이미지 업데이트"""
        try:
            # 현재 캔버스 크기 가져오기
            canvas.update_idletasks()
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            # 이미지 크기에 맞게 캔버스 크기 조정이 필요한지 확인
            image = item['image']
            
            # 이미지를 캔버스에 맞게 스케일링
            if canvas_width > 0 and canvas_height > 0:
                # 기존 배경 이미지 삭제
                canvas.delete('background')
                
                # 새 이미지를 캔버스에 표시
                image_ratio = image.width / image.height
                canvas_ratio = canvas_width / canvas_height
                
                if image_ratio > canvas_ratio:
                    # 이미지가 더 넓음 - 너비에 맞춤
                    display_width = canvas_width
                    display_height = int(canvas_width / image_ratio)
                else:
                    # 이미지가 더 높음 - 높이에 맞춤
                    display_height = canvas_height
                    display_width = int(canvas_height * image_ratio)
                
                # 이미지 리사이즈 및 표시 (투명도 지원 개선)
                display_image = image.resize((display_width, display_height), Image.Resampling.LANCZOS)
                
                # RGBA 이미지 처리 개선
                if display_image.mode == 'RGBA':
                    # 체커보드 배경 생성
                    checker_bg = self.create_checker_background(display_width, display_height)
                    # 투명 이미지를 체커보드 위에 합성
                    final_image = Image.alpha_composite(checker_bg, display_image)
                    canvas_image = ImageTk.PhotoImage(final_image)
                else:
                    canvas_image = ImageTk.PhotoImage(display_image)
                
                # 캔버스 중앙에 이미지 배치
                x = (canvas_width - display_width) // 2
                y = (canvas_height - display_height) // 2
                canvas.create_image(x, y, anchor='nw', image=canvas_image, tags='background')
                
                # 이미지 참조 유지 (가비지 컬렉션 방지)
                canvas.image = canvas_image
                
                logger.debug(f"캔버스 이미지 업데이트 완료: {display_width}x{display_height}")
            
        except Exception as e:
            logger.debug(f"캔버스 이미지 업데이트 오류: {e}")

    def create_checker_background(self, width, height, checker_size=16):
        """투명도 표시용 체커보드 배경 생성"""
        try:
            # RGBA 모드로 체커보드 생성
            checker_bg = Image.new('RGBA', (width, height), (255, 255, 255, 255))
            
            # 체커보드 패턴 그리기
            for y in range(0, height, checker_size):
                for x in range(0, width, checker_size):
                    # 격자 패턴으로 회색과 흰색 번갈아가며
                    if (x // checker_size + y // checker_size) % 2 == 0:
                        color = (220, 220, 220, 255)  # 연한 회색
                    else:
                        color = (255, 255, 255, 255)  # 흰색
                    
                    # 실제 체커 사각형 크기 계산
                    end_x = min(x + checker_size, width)
                    end_y = min(y + checker_size, height)
                    
                    # 픽셀별로 칠하기 (작은 영역이므로 속도 무관)
                    for py in range(y, end_y):
                        for px in range(x, end_x):
                            checker_bg.putpixel((px, py), color)
            
            return checker_bg
            
        except Exception as e:
            logger.debug(f"체커보드 배경 생성 오류: {e}")
            # 폴백: 흰 배경
            return Image.new('RGBA', (width, height), (255, 255, 255, 255))

    def redraw_canvas_annotations(self, canvas, item_index):
        """특정 캔버스의 주석만 다시 그리기"""
        try:
            if not (0 <= item_index < len(self.feedback_items)):
                return
            
            item = self.feedback_items[item_index]
            
            canvas.delete('annotation')
            canvas.delete('selection_rect')
            
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            self.draw_annotations(canvas, item, canvas_width, canvas_height)
            
            # 선택된 주석들 하이라이트
            if self.selected_annotations and item_index == self.current_index:
                self.highlight_selected_annotations(canvas, canvas_width, canvas_height)
            
            canvas.tag_lower('background')
            canvas.update_idletasks()
            
        except Exception as e:
            logger.error(f"캔버스 주석 다시 그리기 오류: {e}")

    def setup_ui(self):
        """UI 구성 - 레이아웃 개선"""
        try:
            self.create_toolbar()  # 프로젝트 정보 제거, 툴바만
            self.create_annotation_tools()  # 옵션 버튼 이동
            self.create_main_area()
            
        except Exception as e:
            logger.error(f"UI 설정 오류: {e}")
            messagebox.showerror("UI 오류", f"UI 초기화 중 오류가 발생했습니다: {e}")

    def add_copyright_footer(self):
        """하단 저작권 표시"""
        footer_frame = tk.Frame(self.root, bg='#e9ecef', height=25)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        footer_frame.pack_propagate(False)
        
        copyright_text = f"제작: 악어스튜디오 경영기획부 | {COPYRIGHT} | V{VERSION} | www.akeostudio.com"
        copyright_label = tk.Label(footer_frame, text=copyright_text,
                                  bg='#e9ecef', fg='#6c757d', font=('Malgun Gothic', 8))
        copyright_label.pack(expand=True)

    def create_toolbar(self):
        """툴바 - 프로젝트 정보 제거"""
        toolbar_frame = tk.LabelFrame(self.root, text="파일 관리", bg='white', 
                                     padx=15, pady=8, font=self.font_manager.ui_font_bold,
                                     relief='flat', bd=1, highlightbackground='#e0e0e0', 
                                     highlightthickness=1)
        toolbar_frame.pack(fill=tk.X, padx=10, pady=(5, 5))
        
        btn_container = tk.Frame(toolbar_frame, bg='white')
        btn_container.pack(expand=True)
        
        btn_frame = tk.Frame(btn_container, bg='white')
        btn_frame.pack()
        
        # 캡처 버튼들
        if PYAUTOGUI_AVAILABLE:
            tk.Button(btn_frame, text="🎯 영역선택", command=self.capture_area_async,
                     font=self.font_manager.ui_font_bold, 
                     padx=12, pady=5, **self.button_styles['primary']).pack(side=tk.LEFT, padx=3)
            
            tk.Button(btn_frame, text="📸 전체화면", command=self.capture_fullscreen_async,
                     font=self.font_manager.ui_font_bold, 
                     padx=12, pady=5, **self.button_styles['success']).pack(side=tk.LEFT, padx=3)
        else:
            tk.Label(btn_frame, text="⚠️ 캡처 기능 없음 (PyAutoGUI 필요)", bg='#ffc107', fg='black', 
                    font=self.font_manager.ui_font, padx=10, pady=5).pack(side=tk.LEFT, padx=3)
        
        tk.Button(btn_frame, text="📁 이미지", command=self.upload_image_async,
                 font=self.font_manager.ui_font_bold, 
                 padx=12, pady=5, **self.button_styles['warning']).pack(side=tk.LEFT, padx=3)
        
        # 빈 캔버스 생성 버튼
        tk.Button(btn_frame, text="🎨 빈 캔버스", command=self.create_blank_canvas,
                 font=self.font_manager.ui_font_bold, 
                 padx=12, pady=5, **self.button_styles['info']).pack(side=tk.LEFT, padx=3)
        
        # 구분선
        separator1 = tk.Frame(btn_frame, width=2, height=25, bg='#dee2e6')
        separator1.pack(side=tk.LEFT, padx=12)
        
        # 프로젝트 관리
        tk.Button(btn_frame, text="💾 저장", command=self.save_project,
                 font=self.font_manager.ui_font, 
                 padx=10, pady=5, **self.button_styles['secondary']).pack(side=tk.LEFT, padx=3)
        
        tk.Button(btn_frame, text="📂 불러오기", command=self.load_project,
                 font=self.font_manager.ui_font, 
                 padx=10, pady=5, **self.button_styles['secondary']).pack(side=tk.LEFT, padx=3)
        
        # 구분선
        separator2 = tk.Frame(btn_frame, width=2, height=25, bg='#dee2e6')
        separator2.pack(side=tk.LEFT, padx=12)
        
        # 내보내기 버튼들 - PDF 버튼 변경
        if REPORTLAB_AVAILABLE:
            tk.Button(btn_frame, text="📄 PDF 내보내기", command=self.show_pdf_info_dialog,
                     font=self.font_manager.ui_font_bold, 
                     padx=12, pady=5, **self.button_styles['danger']).pack(side=tk.LEFT, padx=3)
        else:
            tk.Label(btn_frame, text="⚠️ PDF 기능 없음 (ReportLab 필요)", bg='#ffc107', fg='black', 
                    font=self.font_manager.ui_font, padx=10, pady=5).pack(side=tk.LEFT, padx=3)
        
        if PANDAS_AVAILABLE:
            tk.Button(btn_frame, text="📊 Excel 내보내기", command=self.export_to_excel_async,
                     font=self.font_manager.ui_font_bold, 
                     padx=12, pady=5, **self.button_styles['success']).pack(side=tk.LEFT, padx=3)
        else:
            tk.Label(btn_frame, text="⚠️ Excel 기능 없음 (pandas 필요)", bg='#ffc107', fg='black', 
                    font=self.font_manager.ui_font, padx=10, pady=5).pack(side=tk.LEFT, padx=3)


    def create_blank_canvas(self):
        """빈 캔버스 생성"""
        try:
            # 바탕색 선택
            color_result = colorchooser.askcolor(title="빈 캔버스 바탕색 선택", color="#ffffff")
            if not color_result[1]:  # 취소된 경우
                return
            
            background_color = color_result[1]
            
            # 최적화된 크기 설정
            canvas_width = 1000
            canvas_height = 800
            
            # 선택된 색상으로 빈 이미지 생성
            blank_image = Image.new('RGB', (canvas_width, canvas_height), background_color)
            
            # 메모리 확인
            if not self.system_monitor.check_memory_limit():
                self.cleanup_memory(force=True)
            
            source_name = f"빈 캔버스 ({background_color})"
            self.add_feedback_item(blank_image, source_name)
            
            # 새로 생성된 캔버스로 스크롤
            self.root.after(100, lambda: self.main_canvas.yview_moveto(1.0))
            
            logger.info(f"빈 캔버스 생성 완료: {canvas_width}x{canvas_height}, 색상: {background_color}")
            self.update_status_message(f"빈 캔버스가 생성되었습니다 (색상: {background_color})")
            
        except Exception as e:
            logger.error(f"빈 캔버스 생성 오류: {e}")
            messagebox.showerror('오류', f'빈 캔버스 생성 중 오류가 발생했습니다: {str(e)}')

    def export_to_excel_async(self):
        """비동기 Excel 내보내기"""
        if not PANDAS_AVAILABLE:
            messagebox.showerror('오류', 
                               'pandas 모듈이 필요합니다.\n\n설치 방법:\n1. 명령 프롬프트(CMD)를 관리자 권한으로 실행\n2. pip install pandas openpyxl 입력')
            return
        
        if not self.feedback_items:
            messagebox.showwarning('내보내기', '내보낼 피드백이 없습니다.')
            return

        try:
            free_space = self.system_monitor.get_disk_space(os.getcwd())
            if free_space < 100:
                messagebox.showwarning('디스크 공간 부족', 
                                     f'사용 가능한 디스크 공간이 부족합니다.\n여유 공간: {free_space:.1f}MB')
                return
            
            current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            project_title = self.project_title.get().strip()
            if project_title:
                default_filename = f"{project_title}_피드백목록_{current_time}.xlsx"
            else:
                default_filename = f"피드백목록_{current_time}.xlsx"
            
            file_path = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[
                    ('Excel 파일', '*.xlsx'), 
                    ('CSV 파일', '*.csv'),
                    ('모든 파일', '*.*')
                ],
                initialfile=default_filename
            )
            
            if not file_path:
                return
            
            progress = AdvancedProgressDialog(self.root, "Excel 내보내기", 
                                            "데이터를 준비하고 있습니다...", cancelable=True)
            
            def export_worker():
                """Excel 내보내기 작업자"""
                try:
                    if progress.canceled:
                        return None
                    
                    self.root.after(0, lambda: progress.update(10, "컬럼 구성 중..."))
                    
                    columns = []
                    if self.show_index_numbers.get():
                        columns.append("번호")
                    if self.show_name.get():
                        columns.append("이름")
                    if self.show_timestamp.get():
                        columns.append("작성 일시")
                    columns.append("피드백 내용")
                    columns.append("주석 텍스트")  # 새로 추가
                    
                    if progress.canceled:
                        return None
                    
                    self.root.after(0, lambda: progress.update(30, "데이터 수집 중..."))
                    
                    data_rows = []
                    for i, item in enumerate(self.feedback_items):
                        if progress.canceled:
                            return None
                        
                        row_data = {}
                        
                        if "번호" in columns:
                            row_data["번호"] = i + 1
                        
                        if "이름" in columns:
                            row_data["이름"] = item.get('name', f'피드백 #{i + 1}')
                        
                        if "작성 일시" in columns:
                            row_data["작성 일시"] = item.get('timestamp', '알 수 없음')
                        
                        feedback_text = item.get('feedback_text', '').strip()
                        row_data["피드백 내용"] = feedback_text if feedback_text else '(내용 없음)'
                        
                        # 🔥 주석 텍스트 수집
                        text_annotations = []
                        for ann in item.get('annotations', []):
                            if ann['type'] == 'text':
                                text_content = ann.get('text', '').strip()
                                if text_content:
                                    text_annotations.append(text_content)
                        
                        row_data["주석 텍스트"] = '\n'.join(text_annotations) if text_annotations else '(없음)'
                        
                        data_rows.append(row_data)
                        
                        progress_val = 30 + (i / len(self.feedback_items)) * 40
                        self.root.after(0, lambda p=progress_val, idx=i: progress.update(p, f"데이터 처리 중... ({idx+1}/{len(self.feedback_items)})"))
                    
                    if progress.canceled:
                        return None
                    
                    self.root.after(0, lambda: progress.update(70, "데이터프레임 생성 중..."))
                    
                    df = pd.DataFrame(data_rows, columns=columns)
                    
                    if progress.canceled:
                        return None
                    
                    self.root.after(0, lambda: progress.update(90, "파일 저장 중..."))
                    
                    if file_path.lower().endswith('.csv'):
                        df.to_csv(file_path, index=False, encoding='utf-8-sig')
                    else:
                        df.to_excel(file_path, index=False, engine='openpyxl')
                    
                    if progress.canceled:
                        return None
                    
                    self.root.after(0, lambda: progress.update(100, "완료!"))
                    
                    return {
                        'file_path': file_path,
                        'item_count': len(self.feedback_items),
                        'columns': columns
                    }
                    
                except Exception as e:
                    logger.error(f"Excel 내보내기 오류: {e}")
                    return {'error': str(e)}
            
            def on_export_complete(result):
                """내보내기 완료 콜백"""
                progress.close()
                
                if result is None:
                    return
                
                if 'error' in result:
                    messagebox.showerror('내보내기 오류', f'파일 생성 중 오류가 발생했습니다:\n{result["error"]}')
                    return
                
                file_name = Path(result['file_path']).name
                item_count = result['item_count']
                column_info = ', '.join(result['columns'])
                
                success_msg = f"""✅ 내보내기 완료!

📁 파일: {file_name}
📊 항목 수: {item_count}개
📋 포함 컬럼: {column_info}

파일이 성공적으로 생성되었습니다."""
                
                messagebox.showinfo('내보내기 완료', success_msg)
                logger.info(f"엑셀 내보내기 성공: {result['file_path']} ({item_count}개 항목)")
            
            def on_export_error(error):
                """내보내기 오류 콜백"""
                progress.close()
                messagebox.showerror('내보내기 오류', f'파일 생성 중 오류가 발생했습니다:\n{str(error)}')
            
            self.task_manager.submit_task(
                export_worker,
                callback=on_export_complete,
                error_callback=on_export_error
            )
            
        except Exception as e:
            logger.error(f"Excel 내보내기 준비 오류: {e}")
            messagebox.showerror('내보내기 오류', f'내보내기 준비 중 오류가 발생했습니다:\n{str(e)}')

    def create_tooltip(self, widget, text):
        """위젯에 툴팁 추가"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            tooltip_label = tk.Label(tooltip, text=text, 
                                   background="lightyellow", 
                                   relief="solid", 
                                   borderwidth=1,
                                   font=self.font_manager.ui_font_small)
            tooltip_label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            tooltip.after(3000, hide_tooltip)  # 3초 후 자동 사라짐
            widget.tooltip = tooltip
        
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)

    def create_annotation_tools(self):
        """주석 도구 - 기능별 구분된 한 줄 배치"""
        tools_frame = tk.LabelFrame(self.root, text="주석 도구", bg='white', 
                                   padx=15, pady=8, font=self.font_manager.ui_font_bold,
                                   relief='flat', bd=1, highlightbackground='#e0e0e0', 
                                   highlightthickness=1)
        tools_frame.pack(fill=tk.X, padx=10, pady=(3, 5))
        
        main_container = tk.Frame(tools_frame, bg='white')
        main_container.pack(expand=True)
        
        tools_row = tk.Frame(main_container, bg='white')
        tools_row.pack()
        
        # 🔥 1. 선택 도구 (노란색 배경으로 구분)
        select_frame = tk.Frame(tools_row, bg='#fff9c4', relief='solid', bd=1)
        select_frame.pack(side=tk.LEFT, padx=(0, 8))
        
        self.tool_var = tk.StringVar(value='arrow')
        
        select_btn = tk.Radiobutton(select_frame, text="🔰 선택", 
                                  variable=self.tool_var, value='select',
                                  command=lambda: self.set_tool('select'),
                                  bg='#fff9c4', font=self.font_manager.ui_font_small,
                                  indicatoron=0, relief='flat', bd=0,
                                  selectcolor='#ffeb3b', activebackground='#ffeb3b',
                                  activeforeground='#f57f17',
                                  padx=8, pady=3)
        select_btn.pack(side=tk.LEFT)
        
        # 🔥 선택 도구 툴팁 추가
        self.create_tooltip(select_btn, 
                          "드래그로 여러 주석 선택\n" +
                          "• 텍스트와 이미지 주석 이동/삭제 가능\n" +
                          "• Delete 키로 삭제\n" +
                          "• Ctrl+Z로 실행 취소")
        
        # 🔥 2. 그리기 도구들 (파란색 배경으로 구분)
        draw_frame = tk.Frame(tools_row, bg='#e3f2fd', relief='solid', bd=1)
        draw_frame.pack(side=tk.LEFT, padx=(0, 8))
        
        draw_tools = [
            ('➜ 화살표', 'arrow'),
            ('➖ 라인', 'line'),
            ('✏️ 펜', 'pen'), 
            ('⭕ 원', 'oval'), 
            ('⬜ 사각형', 'rect')
        ]
        
        for text, tool in draw_tools:
            btn = tk.Radiobutton(draw_frame, text=text, 
                               variable=self.tool_var, value=tool,
                               command=lambda t=tool: self.set_tool(t),
                               bg='#e3f2fd', font=self.font_manager.ui_font_small,
                               indicatoron=0, relief='flat', bd=0,
                               selectcolor='#2196f3', activebackground='#2196f3',
                               activeforeground='white',
                               padx=8, pady=3)
            btn.pack(side=tk.LEFT, padx=1)
        
        # 🔥 2-1. 그리기 도구 설정을 그리기 도구 프레임 안에 배치
        # 색상 버튼
        tk.Label(draw_frame, text="색상", bg='#e3f2fd', 
                font=self.font_manager.ui_font_small, fg='#1976d2').pack(side=tk.LEFT, padx=(8, 2))
        self.color_button = tk.Button(draw_frame, text="", bg=self.annotation_color, 
                                     width=8, height=8, command=self.choose_color, 
                                     relief='solid', bd=1, cursor='hand2',
                                     font=('TkDefaultFont', 1))
        self.color_button.pack(side=tk.LEFT, padx=(0, 6), pady=3)
        
        # 두께 스핀박스
        tk.Label(draw_frame, text="두께", bg='#e3f2fd', 
                font=self.font_manager.ui_font_small, fg='#1976d2').pack(side=tk.LEFT, padx=(0, 2))
        self.width_var = tk.StringVar(value=str(self.line_width))
        width_spinbox = tk.Spinbox(draw_frame, from_=1, to=30, width=2, 
                                  textvariable=self.width_var, command=self.update_line_width, 
                                  font=self.font_manager.ui_font_small,
                                  relief='solid', bd=1, bg='white')
        width_spinbox.pack(side=tk.LEFT, padx=(0, 3))
        width_spinbox.bind('<KeyRelease>', lambda e: self.update_line_width())
        
        # 🔥 3. 텍스트 도구 (초록색 배경으로 구분)
        text_frame = tk.Frame(tools_row, bg='#e8f5e8', relief='solid', bd=1)
        text_frame.pack(side=tk.LEFT, padx=(0, 8))
        
        text_btn = tk.Radiobutton(text_frame, text="[T] 텍스트", 
                                variable=self.tool_var, value='text',
                                command=lambda: self.set_tool('text'),
                                bg='#e8f5e8', font=self.font_manager.ui_font_small,
                                indicatoron=0, relief='flat', bd=0,
                                selectcolor='#4caf50', activebackground='#4caf50',
                                activeforeground='white',
                                padx=8, pady=3)
        text_btn.pack(side=tk.LEFT)
        
        # 🔥 4. 특수 도구 (분홍색 배경으로 구분)
        special_frame = tk.Frame(tools_row, bg='#fce4ec', relief='solid', bd=1)
        special_frame.pack(side=tk.LEFT, padx=(0, 8))
        
        capture_btn = tk.Radiobutton(special_frame, text="📷 견본캡처", 
                                   variable=self.tool_var, value='capture_image',
                                   command=lambda: self.set_tool('capture_image'),
                                   bg='#fce4ec', font=self.font_manager.ui_font_small,
                                   indicatoron=0, relief='flat', bd=0,
                                   selectcolor='#e91e63', activebackground='#e91e63',
                                   activeforeground='white',
                                   padx=8, pady=3)
        capture_btn.pack(side=tk.LEFT)
        
        # 구분선
        separator = tk.Frame(tools_row, width=1, height=25, bg='#dee2e6')
        separator.pack(side=tk.LEFT, padx=15)
        
        # 🔥 6. 관리 버튼들
        action_frame = tk.Frame(tools_row, bg='white')
        action_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Button(action_frame, text="🧹 주석 지우기", command=self.clear_current_annotations,
                 font=self.font_manager.ui_font_small, 
                 padx=8, pady=3, **self.button_styles['danger']).pack(side=tk.LEFT, padx=3)
        
        tk.Button(action_frame, text="⚙️ 옵션", command=self.create_options_dialog,
                 font=self.font_manager.ui_font_small, 
                 padx=8, pady=3, **self.button_styles['info']).pack(side=tk.LEFT, padx=3)

    def choose_text_color(self):
        """텍스트 전용 색상 선택"""
        color = colorchooser.askcolor(title="텍스트 색상 선택")[1]
        if color:
            self.annotation_color = color
            self.text_color_button.config(bg=color)
            self.color_button.config(bg=color)  # 기본 색상도 동기화
            logger.debug(f"텍스트 색상 변경: {color}")
    
    def update_font_size_slider(self, value):
        """폰트 크기 슬라이더 업데이트"""
        self.font_size = int(float(value))
        self.font_size_label.config(text=f"{self.font_size}px")
        # 기존 폰트 변수도 동기화
        if hasattr(self, 'font_var'):
            self.font_var.set(str(self.font_size))
        logger.debug(f"폰트 크기 변경: {self.font_size}px")

    def create_options_dialog(self):
        """옵션 다이얼로그 생성"""
        try:
            dialog = tk.Toplevel(self.root)
            dialog.title("옵션")
            
            # 🔥 아이콘 설정
            setup_window_icon(dialog)
            
            # 🔥 화면 해상도에 따른 적응형 크기 설정
            screen_width = dialog.winfo_screenwidth()
            screen_height = dialog.winfo_screenheight()
            
            # 기본 크기 계산 (화면 크기 고려, 최소/최대 제한)
            dialog_width = max(520, min(700, int(screen_width * 0.35)))
            dialog_height = max(700, min(900, int(screen_height * 0.75)))
            
            dialog.geometry(f"{dialog_width}x{dialog_height}")
            dialog.resizable(True, True)  # 🔥 크기 조정 가능
            dialog.minsize(480, 650)      # 🔥 최소 크기 설정
            dialog.maxsize(800, int(screen_height * 0.9))  # 🔥 최대 크기 설정
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 메인 프레임
            main_frame = tk.Frame(dialog, bg='white')
            main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
            
            # PDF 품질 설정
            pdf_frame = tk.LabelFrame(main_frame, text="PDF 품질 설정", 
                                    bg='white', font=self.font_manager.ui_font)
            pdf_frame.pack(fill=tk.X, pady=(0, 15))
            
            quality_frame = tk.Frame(pdf_frame, bg='white')
            quality_frame.pack(fill=tk.X, padx=10, pady=10)
            tk.Label(quality_frame, text="해상도 (DPI):", 
                    bg='white', font=self.font_manager.ui_font).pack(side=tk.LEFT)
            quality_spinbox = tk.Spinbox(quality_frame, from_=150, to=400, increment=50,
                                      textvariable=self.pdf_quality, width=5,
                                      font=self.font_manager.ui_font)
            quality_spinbox.pack(side=tk.LEFT, padx=(5,0))
            tk.Label(quality_frame, text="DPI", 
                    bg='white', font=self.font_manager.ui_font).pack(side=tk.LEFT, padx=(5,0))
            
            def on_quality_change(event=None):
                self.save_settings()
            quality_spinbox.bind('<FocusOut>', on_quality_change)
            quality_spinbox.bind('<Return>', on_quality_change)
            
            # 캔버스 크기 설정
            canvas_frame = tk.LabelFrame(main_frame, text="캔버스 크기 설정", 
                                       bg='white', font=self.font_manager.ui_font)
            canvas_frame.pack(fill=tk.X, pady=(0, 15))
            
            width_frame = tk.Frame(canvas_frame, bg='white')
            width_frame.pack(fill=tk.X, padx=10, pady=5)
            tk.Label(width_frame, text="기본 너비:", 
                    bg='white', font=self.font_manager.ui_font).pack(side=tk.LEFT)
            width_spinbox = tk.Spinbox(width_frame, from_=800, to=1600, increment=100,
                                     textvariable=self.canvas_width, width=5,
                                     font=self.font_manager.ui_font)
            width_spinbox.pack(side=tk.LEFT, padx=(5,0))
            tk.Label(width_frame, text="픽셀", 
                    bg='white', font=self.font_manager.ui_font).pack(side=tk.LEFT, padx=(5,0))
            
            height_frame = tk.Frame(canvas_frame, bg='white')
            height_frame.pack(fill=tk.X, padx=10, pady=5)
            tk.Label(height_frame, text="기본 높이:", 
                    bg='white', font=self.font_manager.ui_font).pack(side=tk.LEFT)
            height_spinbox = tk.Spinbox(height_frame, from_=600, to=1200, increment=100,
                                      textvariable=self.canvas_height, width=5,
                                      font=self.font_manager.ui_font)
            height_spinbox.pack(side=tk.LEFT, padx=(5,0))
            tk.Label(height_frame, text="픽셀", 
                    bg='white', font=self.font_manager.ui_font).pack(side=tk.LEFT, padx=(5,0))
            
            def on_size_change(event=None):
                self.save_settings()
            width_spinbox.bind('<FocusOut>', on_size_change)
            width_spinbox.bind('<Return>', on_size_change)
            height_spinbox.bind('<FocusOut>', on_size_change)
            height_spinbox.bind('<Return>', on_size_change)
            
            # 자동 저장 설정
            save_frame = tk.LabelFrame(main_frame, text="자동 저장 설정", 
                                     bg='white', font=self.font_manager.ui_font)
            save_frame.pack(fill=tk.X, pady=(0, 15))
            
            interval_frame = tk.Frame(save_frame, bg='white')
            interval_frame.pack(fill=tk.X, padx=10, pady=10)
            tk.Label(interval_frame, text="저장 간격:", 
                    bg='white', font=self.font_manager.ui_font).pack(side=tk.LEFT)
            interval_spinbox = tk.Spinbox(interval_frame, from_=1, to=60, width=3,
                                        textvariable=self.auto_save_interval,
                                        font=self.font_manager.ui_font)
            interval_spinbox.pack(side=tk.LEFT, padx=(5,0))
            tk.Label(interval_frame, text="분", 
                    bg='white', font=self.font_manager.ui_font).pack(side=tk.LEFT, padx=(5,0))
            
            def on_interval_change(event=None):
                self.save_settings()
            interval_spinbox.bind('<FocusOut>', on_interval_change)
            interval_spinbox.bind('<Return>', on_interval_change)
            
            # 표시 설정
            display_frame = tk.LabelFrame(main_frame, text="표시 설정", 
                                        bg='white', font=self.font_manager.ui_font)
            display_frame.pack(fill=tk.X, pady=(0, 15))
            
            def on_checkbox_change():
                self.save_settings()
                self.refresh_ui()
            
            check_frame = tk.Frame(display_frame, bg='white')
            check_frame.pack(fill=tk.X, padx=10, pady=10)
            
            tk.Checkbutton(check_frame, text="번호 표시", 
                          variable=self.show_index_numbers,
                          command=on_checkbox_change,
                          bg='white', font=self.font_manager.ui_font).pack(fill=tk.X, pady=2)
            
            tk.Checkbutton(check_frame, text="이름 표시", 
                          variable=self.show_name,
                          command=on_checkbox_change,
                          bg='white', font=self.font_manager.ui_font).pack(fill=tk.X, pady=2)
            
            tk.Checkbutton(check_frame, text="시간 표시", 
                          variable=self.show_timestamp,
                          command=on_checkbox_change,
                          bg='white', font=self.font_manager.ui_font).pack(fill=tk.X, pady=2)

            # 손떨림 방지 옵션 (슬라이더 형식)
            smoothing_frame = tk.LabelFrame(main_frame, text="펜 손떨림 방지", bg='white', font=self.font_manager.ui_font)
            smoothing_frame.pack(fill=tk.X, pady=(0, 15), padx=10)
            
            # 체크박스
            smoothing_check = tk.Checkbutton(
                smoothing_frame, text="손떨림 방지 사용",
                variable=self.pen_smoothing_enabled,
                command=self.save_settings,
                bg='white', font=self.font_manager.ui_font
            )
            smoothing_check.pack(anchor='w', padx=10, pady=(10, 5))
            
            # 슬라이더 영역
            slider_frame = tk.Frame(smoothing_frame, bg='white')
            slider_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            # 강도 라벨
            tk.Label(slider_frame, text="강도:", bg='white', font=self.font_manager.ui_font).pack(side=tk.LEFT)
            
            # 현재 값 표시 라벨
            self.smoothing_value_label = tk.Label(slider_frame, text=f"{self.pen_smoothing_strength.get()}", 
                                                 bg='white', font=(self.font_manager.ui_font[0], 12, 'bold'),
                                                 fg='#2E7D32', width=3)
            self.smoothing_value_label.pack(side=tk.RIGHT, padx=(5, 0))
            
            # 슬라이더
            def on_slider_change(value):
                self.pen_smoothing_strength.set(int(float(value)))
                self.smoothing_value_label.config(text=f"{int(float(value))}")
                self.save_settings()
            
            smoothing_slider = tk.Scale(
                slider_frame, from_=1, to=10, orient=tk.HORIZONTAL,
                variable=self.pen_smoothing_strength,
                command=on_slider_change,
                bg='white', font=self.font_manager.ui_font,
                length=200, sliderlength=20,
                showvalue=0,  # 값 표시 안함 (별도 라벨 사용)
                relief='flat', bd=0
            )
            smoothing_slider.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
            
            # 강도별 설명
            strength_desc = tk.Label(
                smoothing_frame, 
                text="1-3: 가벼운 보정 | 4-6: 적당한 부드러움 | 7-8: 매우 부드러움 | 9-10: 극도로 부드러움",
                bg='white', font=(self.font_manager.ui_font[0], 9), fg='#666'
            )
            strength_desc.pack(padx=10, pady=(0, 10))
            
            # 시스템 정보 표시
            info_frame = tk.LabelFrame(main_frame, text="시스템 정보", 
                                     bg='white', font=self.font_manager.ui_font)
            info_frame.pack(fill=tk.X, pady=(0, 15))
            
            info_inner = tk.Frame(info_frame, bg='white')
            info_inner.pack(fill=tk.X, padx=10, pady=10)
            
            system_info = f"메모리 사용량: {self.system_monitor.get_memory_usage():.1f}MB"
            if len(self.feedback_items) > 0:
                system_info += f"\n피드백 항목 수: {len(self.feedback_items)}개"
            
            tk.Label(info_inner, text=system_info, 
                    bg='white', font=(self.font_manager.ui_font[0], 9)).pack(fill=tk.X)
            
            # 설정 저장 알림
            tk.Label(main_frame, text="※ 설정은 변경 즉시 저장됩니다", 
                    bg='white', fg='#666', 
                    font=(self.font_manager.ui_font[0], 9)).pack(pady=(0, 15))
            
            # 하단 버튼 (기존 UI 디자인과 일치)
            button_frame = tk.Frame(dialog, bg='white')
            button_frame.pack(fill=tk.X, padx=20, pady=(10, 20))
            
            # 도움말 버튼 (통일된 스타일)
            help_button = tk.Button(
                button_frame, text="🔍 도움말", 
                command=self.show_help,
                font=self.font_manager.ui_font,
                padx=15, pady=5,
                **self.button_styles['primary']
            )
            help_button.pack(side=tk.LEFT)
            
            # 메모리 정리 버튼 (통일된 스타일)
            memory_button = tk.Button(
                button_frame, text="🧹 메모리 정리",
                command=lambda: (
                    self.cleanup_memory(force=True),
                    self.update_status_message("메모리 정리 완료")
                ),
                font=self.font_manager.ui_font,
                padx=15, pady=5,
                **self.button_styles['warning']
            )
            memory_button.pack(side=tk.LEFT, padx=(10, 0))
            
            # 업데이트 확인 버튼 (메모리 정리 버튼 옆에 추가)
            if GITHUB_UPDATE_AVAILABLE and self.update_checker:
                update_button = tk.Button(
                    button_frame, text="🔄 업데이트 확인",
                    command=self.manual_update_check,
                    font=self.font_manager.ui_font,
                    padx=15, pady=5,
                    **self.button_styles['info']
                )
                update_button.pack(side=tk.LEFT, padx=(10, 0))
            else:
                update_disabled_button = tk.Button(
                    button_frame, text="⚠️ 업데이트 불가",
                    state='disabled',
                    font=self.font_manager.ui_font,
                    padx=15, pady=5,
                    bg='#f5f5f5', fg='#999999'
                )
                update_disabled_button.pack(side=tk.LEFT, padx=(10, 0))
            
            # 닫기 버튼 (통일된 스타일)
            close_button = tk.Button(
                button_frame, text="닫기", 
                command=dialog.destroy,
                font=self.font_manager.ui_font,
                padx=20, pady=5,
                **self.button_styles['secondary']
            )
            close_button.pack(side=tk.RIGHT)
            
            # 🔥 스마트 창 위치 조정 - 화면 경계 고려
            dialog.update_idletasks()
            dialog_width = dialog.winfo_width()
            dialog_height = dialog.winfo_height()
            screen_width = dialog.winfo_screenwidth()
            screen_height = dialog.winfo_screenheight()
            
            try:
                parent_x = self.root.winfo_x()
                parent_y = self.root.winfo_y()
                parent_width = self.root.winfo_width()
                parent_height = self.root.winfo_height()
                
                # 부모 창 중앙 계산
                x = parent_x + (parent_width - dialog_width) // 2
                y = parent_y + (parent_height - dialog_height) // 2
            except tk.TclError:
                # 부모 창 정보를 가져올 수 없는 경우 화면 중앙으로
                x = (screen_width - dialog_width) // 2
                y = (screen_height - dialog_height) // 2
            
            # 화면 경계 확인 및 조정
            margin = 20
            if x + dialog_width > screen_width - margin:
                x = screen_width - dialog_width - margin
            if x < margin:
                x = margin
            if y + dialog_height > screen_height - 60:  # 작업 표시줄 고려
                y = screen_height - dialog_height - 60
            if y < margin:
                y = margin
            
            dialog.geometry(f"+{x}+{y}")
            
            # 창 닫기 이벤트 처리
            dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
            dialog.bind('<Escape>', lambda e: dialog.destroy())
            
        except Exception as e:
            logger.error(f"옵션 다이얼로그 생성 오류: {e}")
            messagebox.showerror('오류', '옵션 창을 열 수 없습니다.')

    def create_main_area(self):
        """메인 작업 영역"""
        main_frame = tk.LabelFrame(self.root, text="피드백 캔버스", bg='white', 
                                  font=self.font_manager.ui_font_bold, padx=10, pady=8)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 상단 컨트롤 영역
        control_frame = tk.Frame(main_frame, bg='white')
        control_frame.pack(fill=tk.X, pady=(0, 8))
        
        # 왼쪽 컨트롤들
        left_controls = tk.Frame(control_frame, bg='white')
        left_controls.pack(side=tk.LEFT)
        
        tk.Button(left_controls, text="▲ 위로", command=self.move_current_up,
                 font=self.font_manager.ui_font,
                 padx=10, pady=4, **self.button_styles['secondary']).pack(side=tk.LEFT, padx=3)
        
        tk.Button(left_controls, text="▼ 아래로", command=self.move_current_down,
                 font=self.font_manager.ui_font,
                 padx=10, pady=4, **self.button_styles['secondary']).pack(side=tk.LEFT, padx=3)
        
        tk.Button(left_controls, text="📝 이름변경", command=self.rename_current,
                 font=self.font_manager.ui_font,
                 padx=10, pady=4, **self.button_styles['warning']).pack(side=tk.LEFT, padx=3)
        
        tk.Button(left_controls, text="🔳 영역확장", command=self.show_canvas_extension_dialog,
                 font=self.font_manager.ui_font,
                 padx=10, pady=4, **self.button_styles['success']).pack(side=tk.LEFT, padx=3)
        
        tk.Button(left_controls, text="🗑 삭제", command=self.delete_current,
                 font=self.font_manager.ui_font,
                 padx=10, pady=4, **self.button_styles['danger']).pack(side=tk.LEFT, padx=3)
        
        # 중앙 상태 표시
        center_status = tk.Frame(control_frame, bg='white')
        center_status.pack(expand=True)
        
        self.status_label = tk.Label(center_status, text="피드백을 추가하세요", 
                                    bg='white', fg='#495057', 
                                    font=(self.font_manager.ui_font[0], 12, 'bold'))
        self.status_label.pack(expand=True)
        
        # 메인 캔버스 영역 (네비게이션 바와 균형 맞춘 여백)
        canvas_container = tk.Frame(main_frame, bg='white')
        canvas_container.pack(fill=tk.BOTH, expand=True, padx=(8, 2), pady=3)  # 좌우 여백 조정
        
        # 네비게이션 바 생성
        self.navigation_bar = CanvasNavigationBar(canvas_container, self)
        
        # 메인 캔버스 - 선택시에도 회색 테두리 유지
        self.main_canvas = tk.Canvas(canvas_container, bg='#ced4da', 
                                    relief='flat', bd=1,
                                    highlightthickness=2,
                                    highlightbackground='#6c757d',
                                    highlightcolor='#6c757d')
        
        # 🔥 양방향 스크롤바 추가
        self.h_scrollbar = tk.Scrollbar(canvas_container, orient=tk.HORIZONTAL, command=self.main_canvas.xview, width=16)
        self.v_scrollbar = tk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=self.main_canvas.yview, width=30)
        
        # 스크롤 가능 프레임 - 배경 색상 조정  
        self.scrollable_frame = tk.Frame(self.main_canvas, bg='#ced4da',
                                       relief='flat', bd=0)  # 플랫한 스타일
        
        # 🔥 강화된 스크롤 영역 설정
        def on_frame_configure(event):
            # 🔥 안전한 스크롤 영역 업데이트 - after 스케줄링 제거
            try:
                self._force_scroll_update()
            except Exception as e:
                logger.debug(f"configure 이벤트에서 스크롤 업데이트 오류: {e}")
            
        self.scrollable_frame.bind('<Configure>', on_frame_configure)
        
        # 캔버스에 프레임 추가
        self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        
        # 🔥 양방향 스크롤 연결
        self.main_canvas.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)
        
        # 마우스 휠 이벤트 바인딩
        self.main_canvas.bind('<MouseWheel>', self.on_mousewheel)
        self.scrollable_frame.bind('<MouseWheel>', self.on_mousewheel)
        
        # 모든 하위 위젯에도 마우스 휠 이벤트 바인딩
        def bind_mousewheel_to_children(widget):
            widget.bind('<MouseWheel>', self.on_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel_to_children(child)
        
        bind_mousewheel_to_children(self.scrollable_frame)
        
        # 🔥 양방향 스크롤바 배치
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 빈 공간 클릭 시 스크롤 이동 방지
        def prevent_canvas_scroll_to_top(event):
            # 실제 피드백 카드 등 위젯이 아닌 캔버스 빈 공간 클릭 시만 동작
            widget = event.widget
            x, y = event.x, event.y
            # 캔버스 내에 위젯이 있는지 hit test
            overlapping = widget.find_overlapping(x, y, x, y)
            if not overlapping:
                return "break"
        self.main_canvas.bind('<Button-1>', prevent_canvas_scroll_to_top, add='+')

    def set_tool(self, tool):
        """도구 설정"""
        if tool == 'capture_image':
            # 견본 캡처는 즉시 실행
            self.capture_annotation_image()
            return
            
        self.current_tool = tool
        self.tool_var.set(tool)
        # 도구 변경시 선택 해제
        if tool != 'select':
            self.clear_selection()
            
        # 모든 캔버스의 커서를 도구에 맞게 변경
        self.update_canvas_cursors()
        logger.debug(f"도구 변경: {tool}")

    def update_canvas_cursors(self):
        """모든 캔버스의 커서를 현재 도구에 맞게 업데이트"""
        try:
            # 도구별 커서 설정
            cursor_map = {
                'select': 'crosshair',      # 선택: 십자 커서
                'arrow': 'arrow',           # 화살표: 화살표 커서
                'line': 'crosshair',        # 라인: 십자 커서
                'pen': 'target',            # 펜: 동그라미 커서
                'oval': 'crosshair',        # 원형: 십자 커서
                'rect': 'crosshair',        # 사각형: 십자 커서
                'text': 'crosshair'         # 텍스트: 십자 커서
            }
            
            cursor = cursor_map.get(self.current_tool, 'crosshair')
            
            # 모든 활성 캔버스의 커서 업데이트
            if hasattr(self, 'active_canvases'):
                for canvas in self.active_canvases:
                    try:
                        if canvas.winfo_exists():
                            canvas.configure(cursor=cursor)
                    except:
                        pass
                        
            # 피드백 카드의 모든 캔버스 커서 업데이트
            if hasattr(self, 'scrollable_frame') and self.scrollable_frame.winfo_exists():
                for widget in self.scrollable_frame.winfo_children():
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Frame):
                            for grandchild in child.winfo_children():
                                if isinstance(grandchild, tk.Canvas):
                                    try:
                                        grandchild.configure(cursor=cursor)
                                    except:
                                        pass
                                        
        except Exception as e:
            logger.debug(f"커서 업데이트 오류: {e}")
    
    def choose_color(self):
        """색상 선택 - 그리기 도구와 텍스트 색상 동기화"""
        try:
            color = colorchooser.askcolor(color=self.annotation_color, title="주석 색상 선택")
            if color[1]:
                self.annotation_color = color[1]
                self.color_button.configure(bg=self.annotation_color)
                # 텍스트 색상 버튼도 동기화
                if hasattr(self, 'text_color_button'):
                    self.text_color_button.configure(bg=self.annotation_color)
                logger.debug(f"색상 변경: {self.annotation_color}")
        except Exception as e:
            logger.error(f"색상 선택 오류: {e}")

    def update_line_width(self):
        """선 두께 업데이트"""
        try:
            self.line_width = max(1, min(30, int(self.width_var.get())))
        except ValueError:
            self.line_width = 3
            self.width_var.set('3')

    def update_font_size(self):
        """폰트 크기 업데이트"""
        try:
            self.font_size = max(8, min(198, int(self.font_var.get())))
        except ValueError:
            self.font_size = 14
            self.font_var.set('14')

    def clear_current_annotations(self):
        """현재 선택된 피드백의 주석 지우기"""
        if not self.feedback_items:
            self.update_status_message("피드백이 없습니다")
            return
            
        if 0 <= self.current_index < len(self.feedback_items):
            item = self.feedback_items[self.current_index]
            if item.get('annotations', []):
                if messagebox.askyesno('주석 지우기', f'"{item["name"]}"의 모든 주석을 지우시겠습니까?'):
                    self.undo_manager.save_state(item['id'], item['annotations'])
                    item['annotations'].clear()
                    self.clear_selection()  # 선택 해제
                    self.refresh_current_item()
                    self.update_status_message("모든 주석이 삭제되었습니다")
        else:
                self.update_status_message("삭제할 주석이 없습니다")

    def rename_current(self):
        """현재 피드백 이름 변경"""
        try:
            if not self.feedback_items or not (0 <= self.current_index < len(self.feedback_items)):
                messagebox.showwarning('이름 변경', '피드백이 없습니다.')
                return
            item = self.feedback_items[self.current_index]
            new_name = simpledialog.askstring('이름 변경', '새 이름을 입력하세요:', 
                                            initialvalue=item['name'])
            if new_name and new_name.strip():
                item['name'] = new_name.strip()
                self.schedule_ui_refresh()
                self.update_status()
                # UI가 완전히 그려진 후에 스크롤 포커스
                self.root.after_idle(lambda: self.scroll_to_card(self.current_index))
        except Exception as e:
            logger.error(f"이름 변경 오류: {e}")
            messagebox.showerror('오류', f'이름 변경 중 오류가 발생했습니다: {str(e)}')

    def show_canvas_extension_dialog(self):
        """영역확장 다이얼로그 표시 - 수정된 버전"""
        try:
            # 더 정확한 조건 검사
            if not self.feedback_items:
                messagebox.showwarning('영역확장', '확장할 캔버스가 없습니다.')
                return
                
            if not (0 <= self.current_index < len(self.feedback_items)):
                messagebox.showwarning('영역확장', '유효한 캔버스를 선택해주세요.')
                return
            
            logger.debug(f"영역확장 다이얼로그 시작 - 현재 인덱스: {self.current_index}, 총 항목: {len(self.feedback_items)}")
            
            dialog = CanvasExtensionDialog(self.root, self)
            self.root.wait_window(dialog.dialog)
            
            # 결과 확인 및 처리
            if hasattr(dialog, 'result') and dialog.result:
                logger.debug(f"영역확장 설정: {dialog.result}")
                self.extend_canvas(dialog.result)
            else:
                logger.debug("다이얼로그 결과가 없습니다.")
                
        except Exception as e:
            logger.error(f"영역확장 다이얼로그 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            messagebox.showerror('오류', f'영역확장 다이얼로그를 열 수 없습니다: {str(e)}')

    def extend_canvas(self, options):
        """캔버스 영역 확장 실행"""
        try:
            if not self.feedback_items:
                logger.warning("확장할 피드백 항목이 없습니다")
                return
                
            if not (0 <= self.current_index < len(self.feedback_items)):
                logger.warning(f"유효하지 않은 인덱스: {self.current_index}")
                return
            
            # 실행 취소를 위한 상태 저장
            current_item = self.feedback_items[self.current_index]
            self.undo_manager.save_state(current_item['id'], current_item['annotations'])
            
            original_image = current_item['image']
            orig_width = original_image.width
            orig_height = original_image.height
            
            direction = options['direction']
            percentage = options['percentage']
            bg_color = options['bg_color']
            transparent = options['transparent']
            
            # 새 크기 계산
            if direction in ['right', 'left']:
                add_width = int(orig_width * percentage / 100)
                new_width = orig_width + add_width
                new_height = orig_height
            else:  # up, down
                add_height = int(orig_height * percentage / 100)
                new_width = orig_width
                new_height = orig_height + add_height
            
            # 새 이미지 생성
            if transparent:
                new_image = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
            else:
                new_image = Image.new('RGB', (new_width, new_height), bg_color)
            
            # 원본 이미지 위치 계산
            if direction == 'right':
                paste_x, paste_y = 0, 0
            elif direction == 'left':
                paste_x, paste_y = add_width, 0
            elif direction == 'down':
                paste_x, paste_y = 0, 0
            else:  # up
                paste_x, paste_y = 0, add_height
            
            # 원본 이미지 붙이기
            if original_image.mode == 'RGBA' or transparent:
                new_image.paste(original_image, (paste_x, paste_y), original_image if 'A' in original_image.mode else None)
            else:
                new_image.paste(original_image, (paste_x, paste_y))
            
            # 주석 위치 조정
            if direction == 'left':
                for ann in current_item['annotations']:
                    if 'x' in ann:
                        ann['x'] += add_width
                    if 'start_x' in ann:
                        ann['start_x'] += add_width
                    if 'end_x' in ann:
                        ann['end_x'] += add_width
                    if 'x1' in ann:
                        ann['x1'] += add_width
                    if 'x2' in ann:
                        ann['x2'] += add_width
                    if ann['type'] == 'pen' and 'points' in ann:
                        ann['points'] = [(x + add_width, y) for x, y in ann['points']]
            elif direction == 'up':
                for ann in current_item['annotations']:
                    if 'y' in ann:
                        ann['y'] += add_height
                    if 'start_y' in ann:
                        ann['start_y'] += add_height
                    if 'end_y' in ann:
                        ann['end_y'] += add_height
                    if 'y1' in ann:
                        ann['y1'] += add_height
                    if 'y2' in ann:
                        ann['y2'] += add_height
                    if ann['type'] == 'pen' and 'points' in ann:
                        ann['points'] = [(x, y + add_height) for x, y in ann['points']]
            
            # 이미지 교체
            current_item['image'] = new_image
            
            logger.info(f"캔버스 확장 완료: {orig_width}x{orig_height} -> {new_width}x{new_height}")
            
            # UI 새로고침 - 전체 UI 강제 재생성
            self.schedule_ui_refresh()
            
            # 약간의 지연 후 현재 아이템으로 스크롤
            self.root.after(100, lambda: self.scroll_to_card(self.current_index))
            
            self.update_status_message(f"캔버스가 {direction} 방향으로 {percentage}% 확장되었습니다 ({new_width}x{new_height})")
            
        except Exception as e:
            logger.error(f"캔버스 확장 오류: {e}")
            messagebox.showerror('오류', f'캔버스 확장 중 오류가 발생했습니다: {str(e)}')

    def capture_fullscreen_async(self):
        """비동기 전체 화면 캡처"""
        if not PYAUTOGUI_AVAILABLE:
            messagebox.showerror('오류', 'PyAutoGUI 모듈이 설치되지 않았습니다.\n\n설치 방법:\n1. 명령 프롬프트(CMD)를 관리자 권한으로 실행\n2. pip install pyautogui 입력')
            return
        
        def capture_worker():
            """캡처 작업자"""
            try:
                if not self.system_monitor.check_memory_limit():
                    return {'error': '메모리 사용량이 높습니다. 메모리 정리 후 다시 시도해주세요.'}
                
                self.root.after(0, self.root.withdraw)
                time.sleep(1.0)
                
                # 다중 모니터 지원을 위한 MSS 사용
                if MSS_AVAILABLE:
                    with mss.mss() as sct:
                        # 모든 모니터를 포함하는 전체 화면 캡처
                        monitor = sct.monitors[0]  # 0은 모든 모니터를 포함
                        screenshot = sct.grab(monitor)
                        # PIL Image로 변환
                        screenshot = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                else:
                    # PyAutoGUI 폴백 (단일 모니터만 지원)
                    screenshot = pyautogui.screenshot()
                
                # 🔥 옵션에 따라 이미지 최적화 수행
                screenshot = self.optimize_image(screenshot)
                
                return {'image': screenshot, 'name': '전체화면 캡처'}
                
            except Exception as e:
                logger.error(f"전체화면 캡처 오류: {e}")
                return {'error': f'화면 캡처 중 오류가 발생했습니다: {str(e)}'}
        
        def on_capture_complete(result):
            """캡처 완료 콜백"""
            self.root.deiconify()
            
            if 'error' in result:
                messagebox.showerror('캡처 오류', result['error'])
                return
            
            self.add_feedback_item(result['image'], result['name'])
        
        def on_capture_error(error):
            """캡처 오류 콜백"""
            self.root.deiconify()
            messagebox.showerror('캡처 오류', f'화면 캡처 중 오류가 발생했습니다: {str(error)}')
        
        self.task_manager.submit_task(
            capture_worker,
            callback=on_capture_complete,
            error_callback=on_capture_error
        )

    def capture_area_async(self):
        """비동기 영역 선택 캡처"""
        if not PYAUTOGUI_AVAILABLE:
            messagebox.showerror('오류', 'PyAutoGUI 모듈이 설치되지 않았습니다.\n\n설치 방법:\n1. 명령 프롬프트(CMD)를 관리자 권한으로 실행\n2. pip install pyautogui 입력')
            return
        
        def start_selection():
            """선택 시작"""
            try:
                if not self.system_monitor.check_memory_limit():
                    return {'error': '메모리 사용량이 높습니다. 메모리 정리 후 다시 시도해주세요.'}
                
                self.root.after(0, self.root.withdraw)
                time.sleep(0.5)
                self.root.after(0, self.create_selection_window)
                
            except Exception as e:
                logger.error(f"영역 캡처 준비 오류: {e}")
                return {'error': f'영역 캡처 준비 중 오류가 발생했습니다: {str(e)}'}
        
        self.task_manager.submit_task(start_selection)

    def create_selection_window(self):
        """영역 선택 창"""
        try:
            overlay = tk.Toplevel()
            
            # 다중 모니터 전체 화면 크기 계산
            if MSS_AVAILABLE:
                with mss.mss() as sct:
                    monitor = sct.monitors[0]  # 모든 모니터
                    total_width = monitor['width']
                    total_height = monitor['height']
                    left = monitor['left']
                    top = monitor['top']
            else:
                # 폴백: tkinter로 가상 화면 크기 가져오기
                total_width = overlay.winfo_vrootwidth()
                total_height = overlay.winfo_vrootheight()
                left = 0
                top = 0
            
            overlay.geometry(f'{total_width}x{total_height}+{left}+{top}')
            overlay.attributes('-fullscreen', True)
            overlay.attributes('-alpha', 0.3)
            overlay.configure(bg='black', cursor='crosshair')
            overlay.attributes('-topmost', True)
            
            info_label = tk.Label(overlay, text="마우스로 드래그하여 캡처할 영역을 선택하세요. ESC: 취소",
                                bg='yellow', fg='black', font=self.font_manager.title_font)
            info_label.place(x=50, y=50)
            
            canvas = tk.Canvas(overlay, bg='black', highlightthickness=0, cursor='crosshair')
            canvas.pack(fill=tk.BOTH, expand=True)
            
            selection = {'start_x': 0, 'start_y': 0, 'rect_id': None}
            
            def start_selection(event):
                selection['start_x'] = event.x_root
                selection['start_y'] = event.y_root
                if selection['rect_id']:
                    canvas.delete(selection['rect_id'])
            
            def update_selection(event):
                if selection['rect_id']:
                    canvas.delete(selection['rect_id'])
                selection['rect_id'] = canvas.create_rectangle(
                    selection['start_x'], selection['start_y'],
                    event.x_root, event.y_root,
                    outline='red', width=2
                )
            
            def finish_selection(event):
                try:
                    overlay.destroy()
                    
                    x1 = min(selection['start_x'], event.x_root)
                    y1 = min(selection['start_y'], event.y_root)
                    width = abs(event.x_root - selection['start_x'])
                    height = abs(event.y_root - selection['start_y'])
                    
                    if width > 10 and height > 10:
                        def capture_region():
                            try:
                                time.sleep(0.2)
                                if MSS_AVAILABLE:
                                    with mss.mss() as sct:
                                        monitor = {"top": y1, "left": x1, "width": width, "height": height}
                                        screenshot = sct.grab(monitor)
                                        # PIL Image로 변환
                                        screenshot = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                                else:
                                    # PyAutoGUI 폴백
                                    screenshot = pyautogui.screenshot(region=(x1, y1, width, height))
                                
                                # 🔥 옵션에 따라 이미지 최적화 수행
                                screenshot = self.optimize_image(screenshot)
                                return {'image': screenshot, 'name': '영역 캡처'}
                            except Exception as e:
                                return {'error': str(e)}
                        
                        def on_region_capture_complete(result):
                            self.root.deiconify()
                            if 'error' in result:
                                messagebox.showerror('캡처 오류', f'영역 캡처 중 오류가 발생했습니다: {result["error"]}')
                            else:
                                self.add_feedback_item(result['image'], result['name'])
                        
                        self.task_manager.submit_task(
                            capture_region,
                            callback=on_region_capture_complete,
                            error_callback=lambda e: (self.root.deiconify(), messagebox.showerror('캡처 오류', str(e)))
                        )
                    else:
                        self.root.deiconify()
                        
                except Exception as e:
                    logger.error(f"영역 캡처 완료 오류: {e}")
                    self.root.deiconify()
            
            def cancel_selection(event):
                overlay.destroy()
                self.root.deiconify()
            
            canvas.bind('<ButtonPress-1>', start_selection)
            canvas.bind('<B1-Motion>', update_selection)
            canvas.bind('<ButtonRelease-1>', finish_selection)
            overlay.bind('<Escape>', cancel_selection)
            overlay.focus_force()
            
        except Exception as e:
            logger.error(f"선택 창 생성 오류: {e}")
            self.root.deiconify()
            messagebox.showerror('오류', f'영역 선택 창 생성 중 오류가 발생했습니다: {str(e)}')

    def capture_annotation_image(self):
        """주석 이미지를 위한 영역 캡처"""
        if not PYAUTOGUI_AVAILABLE:
            messagebox.showerror('오류', 'PyAutoGUI 모듈이 설치되지 않았습니다.')
            return
        
        if not self.feedback_items or not (0 <= self.current_index < len(self.feedback_items)):
            messagebox.showwarning('견본 캡처', '캔버스를 먼저 선택해주세요.')
            return
        
        def start_selection():
            try:
                self.root.after(0, self.root.withdraw)
                time.sleep(0.5)
                self.root.after(0, lambda: self.create_annotation_image_selection_window())
            except Exception as e:
                logger.error(f"견본 캡처 준비 오류: {e}")
                self.root.deiconify()
        
        self.task_manager.submit_task(start_selection)

    def create_annotation_image_selection_window(self):
        """주석 이미지 선택 창"""
        try:
            overlay = tk.Toplevel()
            
            # 화면 전체 크기 설정 (기존 영역 캡처와 동일)
            if MSS_AVAILABLE:
                with mss.mss() as sct:
                    monitor = sct.monitors[0]
                    total_width = monitor['width']
                    total_height = monitor['height']
                    left = monitor['left']
                    top = monitor['top']
            else:
                total_width = overlay.winfo_vrootwidth()
                total_height = overlay.winfo_vrootheight()
                left = 0
                top = 0
            
            overlay.geometry(f'{total_width}x{total_height}+{left}+{top}')
            overlay.attributes('-fullscreen', True)
            overlay.attributes('-alpha', 0.3)
            overlay.configure(bg='black', cursor='crosshair')
            overlay.attributes('-topmost', True)
            
            info_label = tk.Label(overlay, text="마우스로 드래그하여 견본 이미지를 선택하세요. ESC: 취소",
                                bg='yellow', fg='black', font=self.font_manager.title_font)
            info_label.place(x=50, y=50)
            
            canvas = tk.Canvas(overlay, bg='black', highlightthickness=0, cursor='crosshair')
            canvas.pack(fill=tk.BOTH, expand=True)
            
            selection = {'start_x': 0, 'start_y': 0, 'rect_id': None}
            
            def start_selection(event):
                selection['start_x'] = event.x_root
                selection['start_y'] = event.y_root
                if selection['rect_id']:
                    canvas.delete(selection['rect_id'])
            
            def update_selection(event):
                if selection['rect_id']:
                    canvas.delete(selection['rect_id'])
                selection['rect_id'] = canvas.create_rectangle(
                    selection['start_x'], selection['start_y'],
                    event.x_root, event.y_root,
                    outline='red', width=2
                )
            
            def finish_selection(event):
                try:
                    overlay.destroy()
                    
                    x1 = min(selection['start_x'], event.x_root)
                    y1 = min(selection['start_y'], event.y_root)
                    width = abs(event.x_root - selection['start_x'])
                    height = abs(event.y_root - selection['start_y'])
                    
                    if width > 10 and height > 10:
                        def capture_region():
                            try:
                                time.sleep(0.2)
                                if MSS_AVAILABLE:
                                    with mss.mss() as sct:
                                        monitor = {"top": y1, "left": x1, "width": width, "height": height}
                                        screenshot = sct.grab(monitor)
                                        screenshot = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                                else:
                                    screenshot = pyautogui.screenshot(region=(x1, y1, width, height))
                                
                                return {'image': screenshot}
                            except Exception as e:
                                return {'error': str(e)}
                        
                        def on_capture_complete(result):
                            self.root.deiconify()
                            if 'error' in result:
                                messagebox.showerror('캡처 오류', f'견본 캡처 중 오류가 발생했습니다: {result["error"]}')
                            else:
                                self.add_annotation_image(result['image'])
                        
                        self.task_manager.submit_task(
                            capture_region,
                            callback=on_capture_complete
                        )
                    else:
                        self.root.deiconify()
                        
                except Exception as e:
                    logger.error(f"견본 캡처 완료 오류: {e}")
                    self.root.deiconify()
            
            def cancel_selection(event):
                overlay.destroy()
                self.root.deiconify()
            
            canvas.bind('<ButtonPress-1>', start_selection)
            canvas.bind('<B1-Motion>', update_selection)
            canvas.bind('<ButtonRelease-1>', finish_selection)
            overlay.bind('<Escape>', cancel_selection)
            overlay.focus_force()
            
        except Exception as e:
            logger.error(f"선택 창 생성 오류: {e}")
            self.root.deiconify()

    def add_annotation_image(self, image):
        """캡처한 이미지를 현재 캔버스에 주석으로 추가"""
        try:
            if not self.feedback_items or not (0 <= self.current_index < len(self.feedback_items)):
                return
            
            current_item = self.feedback_items[self.current_index]
            
            # 이미지를 base64로 인코딩
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # 이미지 주석 데이터 생성
            annotation = {
                'type': 'image',
                'x': 50,  # 기본 위치
                'y': 50,
                'width': image.width,
                'height': image.height,
                'original_width': image.width,
                'original_height': image.height,
                'image_data': image_b64,
                'opacity': 100,  # 투명도 (0-100)
                'outline': False,  # 아웃라인 여부
                'outline_width': 3,  # 아웃라인 두께
                'rotation': 0,  # 회전 각도
                'flip_horizontal': False,  # 좌우 반전
                'flip_vertical': False  # 상하 반전
            }
            
            # 실행 취소를 위한 상태 저장
            self.undo_manager.save_state(current_item['id'], current_item['annotations'])
            
            # 주석 추가
            current_item['annotations'].append(annotation)
            
            # 화면 새로고침
            self.refresh_current_item()
            

            
            self.update_status_message("견본 이미지가 추가되었습니다")
            logger.info("견본 이미지 주석 추가 완료")
            
        except Exception as e:
            logger.error(f"견본 이미지 추가 오류: {e}")
            messagebox.showerror('오류', '견본 이미지 추가 중 오류가 발생했습니다.')

    def upload_image_async(self):
        """비동기 다중 이미지 업로드"""
        try:
            file_paths = filedialog.askopenfilenames(
                title='이미지 파일 선택 (다중 선택 가능)',
                filetypes=[
                    ('이미지 파일', '*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.webp'), 
                    ('PNG 파일', '*.png'),
                    ('JPEG 파일', '*.jpg *.jpeg'),
                    ('모든 파일', '*.*')
                ]
            )
            
            if not file_paths:
                return
            
            if not self.system_monitor.check_memory_limit():
                messagebox.showwarning('메모리 부족', '메모리 사용량이 높습니다. 메모리 정리 후 다시 시도해주세요.')
                return
            
            if len(file_paths) > 10:
                if not messagebox.askyesno('다중 이미지 업로드', 
                                         f'{len(file_paths)}개의 이미지를 업로드하시겠습니까?\n메모리 사용량이 증가할 수 있습니다.'):
                    return
            
            progress = AdvancedProgressDialog(self.root, "다중 이미지 업로드", 
                                            f"{len(file_paths)}개 이미지를 불러오고 있습니다...", cancelable=True)
            
            def upload_worker():
                """다중 업로드 작업자"""
                try:
                    valid_images = []
                    
                    for i, file_path in enumerate(file_paths):
                        if progress.canceled:
                            return None
                        
                        self.root.after(0, lambda idx=i: progress.update(
                            10 + (idx / len(file_paths)) * 70, 
                            f"파일 검증 중... ({idx+1}/{len(file_paths)})"
                        ))
                        
                        is_valid, error_msg = self.validate_image_file(file_path)
                        if not is_valid:
                            logger.warning(f"이미지 파일 유효성 실패: {Path(file_path).name} - {error_msg}")
                            continue
                        
                        try:
                            image = Image.open(file_path)
                            # 🔥 옵션에 따라 이미지 최적화 수행
                            image = self.optimize_image(image)
                            
                            file_name = Path(file_path).name
                            valid_images.append({
                                'image': image, 
                                'name': f'이미지 업로드: {file_name}',
                                'path': file_path
                            })
                            
                        except Exception as e:
                            logger.warning(f"이미지 로드 실패: {Path(file_path).name} - {str(e)}")
                            continue
                    
                    if progress.canceled:
                        return None
                    
                    self.root.after(0, lambda: progress.update(80, "이미지 처리 완료"))
                    
                    return {
                        'valid_images': valid_images,
                        'total_files': len(file_paths),
                        'success_count': len(valid_images)
                    }
                    
                except Exception as e:
                    logger.error(f"다중 이미지 업로드 오류: {e}")
                    return {'error': f'이미지 로드 중 오류가 발생했습니다: {str(e)}'}
            
            def on_upload_complete(result):
                """업로드 완료 콜백"""
                progress.close()
                
                if result is None:
                    return
                
                if 'error' in result:
                    messagebox.showerror('오류', result['error'])
                    return
                
                valid_images = result['valid_images']
                if not valid_images:
                    messagebox.showwarning('이미지 업로드', '유효한 이미지 파일이 없습니다.')
                    return
                
                def add_images_sequentially():
                    for img_data in valid_images:
                        self.add_feedback_item(img_data['image'], img_data['name'])
                    
                    total = result['total_files']
                    success = result['success_count']
                    
                    if success == total:
                        message = f"✅ {success}개 이미지가 모두 성공적으로 업로드되었습니다!"
                    else:
                        failed = total - success
                        message = f"✅ {success}개 이미지 업로드 성공\n⚠️ {failed}개 파일은 처리할 수 없었습니다."
                    
                    messagebox.showinfo('업로드 완료', message)
                    logger.info(f"다중 이미지 업로드 완료: {success}/{total}")
                
                self.root.after(0, add_images_sequentially)
            
            def on_upload_error(error):
                """업로드 오류 콜백"""
                progress.close()
                messagebox.showerror('오류', f'다중 이미지 업로드 중 오류가 발생했습니다: {str(error)}')
            
            progress.set_cancel_callback(lambda: logger.info("다중 이미지 업로드가 취소되었습니다"))
            
            self.task_manager.submit_task(
                upload_worker,
                callback=on_upload_complete,
                error_callback=on_upload_error
            )
            
        except Exception as e:
            logger.error(f"다중 이미지 업로드 준비 오류: {e}")
            messagebox.showerror('오류', f'이미지 업로드 준비 중 오류가 발생했습니다: {str(e)}')

    def add_feedback_item(self, image, source_type):
        """피드백 항목 추가 - 웹툰 지원 강화"""
        try:
            # 🔥 웹툰 메모리 최적화 강화
            current_memory = self.system_monitor.get_memory_usage()
            logger.info(f"이미지 추가 전 메모리: {current_memory:.1f}MB")
            
            # 메모리 사용량이 높으면 적극적 정리
            if current_memory > 2500 or not self.system_monitor.check_memory_limit():
                logger.warning(f"메모리 압박 상태 ({current_memory:.1f}MB) - 강제 정리 실행")
                self.cleanup_memory(force=True)
                current_memory = self.system_monitor.get_memory_usage()
                logger.info(f"메모리 정리 후: {current_memory:.1f}MB")
            
            # 이미지 최적화 적용
            optimized_image = self.optimize_image(image)
            
            def add_item():
                try:
                    item_id = len(self.feedback_items)
                    feedback_item = {
                        'id': item_id,
                        'name': f"{source_type} #{item_id + 1}",
                        'image': optimized_image,  # 최적화된 이미지 사용
                        'feedback_text': '',
                        'annotations': [],
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source_type': source_type
                    }
                    
                    self.feedback_items.append(feedback_item)
                    self.current_index = len(self.feedback_items) - 1
                    
                    self.undo_manager.save_state(item_id, [])
                    
                    # 🔥 항목이 많을 때 주기적 메모리 정리
                    if len(self.feedback_items) % 5 == 0:  # 5개마다 정리
                        self.cleanup_memory()
                    
                    self.schedule_ui_refresh()
                    self.update_status()
                    
                    # 🔥 웹툰 지원: 스크롤 처리 강화
                    def scroll_to_new_item():
                        try:
                            # 스크롤 영역 강제 업데이트
                            self.scrollable_frame.update_idletasks()
                            bbox = self.main_canvas.bbox('all')
                            if bbox:
                                self.main_canvas.configure(scrollregion=bbox)
                            
                            # 마지막 항목으로 스크롤
                            self.main_canvas.yview_moveto(1.0)
                            logger.debug(f"새 항목으로 스크롤 완료: bbox={bbox}")
                        except Exception as e:
                            logger.debug(f"스크롤 오류: {e}")
                    
                    # 단계별 스크롤 처리 (웹툰과 같은 큰 이미지 고려)
                    self.root.after(300, scroll_to_new_item)  # 첫 번째 시도
                    self.root.after(800, scroll_to_new_item)  # 두 번째 시도
                    self.root.after(1500, scroll_to_new_item) # 최종 확인 (웹툰 로딩 완료 대기)
                    
                    final_memory = self.system_monitor.get_memory_usage()
                    logger.info(f"피드백 항목 추가: {feedback_item['name']} (총 {len(self.feedback_items)}개, 메모리: {final_memory:.1f}MB)")
                    
                except Exception as e:
                    logger.error(f"피드백 항목 추가 오류: {e}")
                    messagebox.showerror('오류', f'피드백 항목 추가 중 오류가 발생했습니다: {str(e)}')
            
            self.root.after(0, add_item)
            
        except Exception as e:
            logger.error(f"피드백 항목 추가 준비 오류: {e}")

    def cleanup_memory(self, force=False):
        """메모리 정리 - 웹툰 지원 강화"""
        try:
            initial_memory = self.system_monitor.get_memory_usage()
            
            # 🔥 강화된 메모리 정리
            if force or initial_memory > 2000:  # 2GB 이상일 때 적극적 정리
                # 1. 실행 취소 히스토리 정리
                for item_id in list(self.undo_manager.histories.keys()):
                    history = self.undo_manager.histories[item_id]
                    # 강제 정리 시 히스토리를 더 적게 유지
                    max_history = 3 if force else 5
                    while len(history) > max_history:
                        history.popleft()
                
                # 2. 이미지 캐시 정리
                if hasattr(self, 'image_cache'):
                    cache_size = len(self.image_cache)
                    if cache_size > 5:  # 5개 이상일 때 정리
                        # 오래된 캐시 항목들 제거
                        cache_keys = list(self.image_cache.keys())
                        remove_count = cache_size - 3  # 3개만 유지
                        for key in cache_keys[:remove_count]:
                            del self.image_cache[key]
                        logger.info(f"이미지 캐시 정리: {cache_size}개 → {len(self.image_cache)}개")
                
                # 3. SmartCanvasViewer 이미지 캐시 정리
                for widget in self.scrollable_frame.winfo_children():
                    try:
                        # 각 카드의 SmartCanvasViewer 찾기
                        for child in widget.winfo_children():
                            if hasattr(child, 'winfo_children'):
                                for grandchild in child.winfo_children():
                                    if hasattr(grandchild, 'canvas') and hasattr(grandchild, 'photo'):
                                        # 이미지 참조 정리
                                        grandchild.canvas.image = None
                                        if hasattr(grandchild, 'photo'):
                                            del grandchild.photo
                    except:
                        pass
            
            # 4. 가비지 컬렉션 여러 번 실행
            for _ in range(3):
                gc.collect()
            
            final_memory = self.system_monitor.get_memory_usage()
            memory_freed = initial_memory - final_memory
            
            if force or memory_freed > 10:  # 10MB 이상 해제되었을 때만 로깅
                logger.info(f"메모리 정리 완료: {memory_freed:.1f}MB 해제 ({initial_memory:.1f}MB → {final_memory:.1f}MB)")
                
                if force:
                    self.update_status_message(f"메모리 정리 완료: {final_memory:.1f}MB 사용 중")
            
        except Exception as e:
            logger.debug(f"메모리 정리 오류: {e}")

    def refresh_ui(self):
        """UI 새로고침 - 웹툰 지원 강화"""
        try:
            for widget in self.scrollable_frame.winfo_children():
                try:
                    widget.destroy()
                except:
                    pass
            
            # 활성 캔버스 목록 초기화
            self.active_canvases = []
            
            # 🔥 피드백 카드들을 순차적으로 생성
            logger.info(f"UI 새로고침 시작: {len(self.feedback_items)}개 항목")
            
            for i, item in enumerate(self.feedback_items):
                self.create_feedback_card(item, i)
                # 진행 상황 로깅 (많은 항목이 있을 때)
                if (i + 1) % 5 == 0 or i == len(self.feedback_items) - 1:
                    logger.debug(f"카드 생성 진행: {i + 1}/{len(self.feedback_items)}")
            
            # 🔥 안전한 스크롤 영역 업데이트 - after 스케줄링 제거
            try:
                # 즉시 스크롤 영역 업데이트
                self.scrollable_frame.update_idletasks()
                self._force_scroll_update()
                logger.debug("UI 새로고침 중 스크롤 영역 업데이트 완료")
            except Exception as e:
                logger.debug(f"스크롤 영역 업데이트 오류: {e}")
            
            # 네비게이션 바 새로고침
            if self.navigation_bar:
                self.navigation_bar.refresh_minimap()
            
            logger.info(f"UI 새로고침 완료: {len(self.feedback_items)}개 카드 생성")
            
        except Exception as e:
            logger.error(f"UI 새로고침 오류: {e}")

    def _force_scroll_update(self):
        """강제 스크롤 영역 업데이트 - 재귀 방지"""
        # 재귀 방지 플래그
        if hasattr(self, '_scroll_updating') and self._scroll_updating:
            return
            
        try:
            self._scroll_updating = True
            
            # 위젯 존재 확인
            if not hasattr(self, 'main_canvas') or not self.main_canvas.winfo_exists():
                return
            if not hasattr(self, 'scrollable_frame') or not self.scrollable_frame.winfo_exists():
                return
                
            # 1단계: 모든 위젯 업데이트
            self.root.update_idletasks()
            self.scrollable_frame.update_idletasks()
            
            # 2단계: 스크롤가능 프레임의 실제 크기 요구량 계산
            self.scrollable_frame.update()
            required_width = self.scrollable_frame.winfo_reqwidth()
            required_height = self.scrollable_frame.winfo_reqheight()
            
            # 3단계: bbox 계산 및 적용 - 🔥 가로 방향도 고려
            bbox = self.main_canvas.bbox('all')
            if bbox:
                x1, y1, x2, y2 = bbox
                # 안전 여백을 크게 증가 (무제한 캔버스 지원)
                large_margin = 200  # 대폭 증가된 여백
                final_width = max(x2, required_width) + large_margin  # 🔥 가로 여백 추가
                final_height = max(y2, required_height) + large_margin
                extended_bbox = (x1, y1, final_width, final_height)
            else:
                # bbox가 없어도 강제로 큰 영역 설정
                large_margin = 200
                final_width = max(800, required_width) + large_margin  # 🔥 가로 여백 추가
                final_height = max(600, required_height) + large_margin
                extended_bbox = (0, 0, final_width, final_height)
            
            # 4단계: 스크롤 영역 설정 (event_generate 제거로 재귀 방지)
            self.main_canvas.configure(scrollregion=extended_bbox)
            
            logger.debug(f"양방향 스크롤 업데이트: {extended_bbox} (실제요구: {required_width}x{required_height})")
            
        except Exception as e:
            logger.debug(f"강제 스크롤 업데이트 오류: {e}")
            # 오류 발생 시도 기본 큰 영역 설정 - 🔥 가로 방향도 고려
            try:
                if hasattr(self, 'main_canvas') and self.main_canvas.winfo_exists():
                    fallback_bbox = (0, 0, 2400, 10000)  # 🔥 가로 크기도 증가 (더 큰 기본 영역)
                    self.main_canvas.configure(scrollregion=fallback_bbox)
                    logger.debug(f"양방향 폴백 스크롤 영역 설정: {fallback_bbox}")
            except:
                pass
        finally:
            # 재귀 방지 플래그 해제
            self._scroll_updating = False

    def create_feedback_card(self, item, index):
        """피드백 카드 생성 - 이벤트 충돌 해결"""
        is_current = (index == self.current_index)
        card_bg = 'white'  # 색상 변경 비활성화 - 항상 흰색
        border_color = '#ddd'  # 테두리도 항상 회색

        title_parts = []
        if self.show_index_numbers.get():
            title_parts.append(f"#{index + 1}")
        if self.show_name.get():
            title_parts.append(item['name'])
        if self.show_timestamp.get():
            title_parts.append(f"({item['timestamp']})")
        title = " ".join(title_parts) if title_parts else f"피드백 #{index + 1}"

        # 피드백 카드 - 선택된 카드만 파란색 테두리, 나머지는 회색
        card = tk.LabelFrame(self.scrollable_frame, text=title,
                            bg=card_bg, fg='#333', font=self.font_manager.ui_font_bold,
                            relief='flat', bd=2,
                            labelanchor='nw')
        
        # 초기 테두리 색상 설정 - 선택된 카드만 파란색
        if is_current:
            card.configure(highlightbackground='#2196F3', highlightcolor='#2196F3', 
                          highlightthickness=2)
        else:
            card.configure(highlightbackground='#dee2e6', highlightcolor='#dee2e6', 
                          highlightthickness=1)
        
        card.pack(fill=tk.X, padx=10, pady=5)
        card.item_index = index
        self.create_context_menu(card, item)

        # 카드 클릭 시 선택 상태 변경
        def on_card_click(event):
            if self.current_index != index:
                self.current_index = index
                self.update_card_borders()  # 모든 카드의 테두리 업데이트
                self.update_status()
                
        card.bind('<Button-1>', on_card_click)

        # 🎯 기존 복잡한 캔버스 대신 스마트 캔버스 뷰어 사용
        image_frame = tk.Frame(card, bg=card_bg)
        image_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        
        # 스마트 캔버스 뷰어 생성 (주석 기능 포함)
        smart_viewer = SmartCanvasViewer(image_frame, item, self, index)
        
        self.create_feedback_text_area(card, item, card_bg, index)

    def create_feedback_text_area(self, parent, item, bg_color, index=None):
        """피드백 텍스트 영역 생성 - 스크롤 최적화"""
        # 텍스트 프레임 - 활성 상태에 따른 테두리
        is_current = (index == self.current_index) if index is not None else False
        border_color = '#2196F3' if is_current else '#dee2e6'
        thickness = 2 if is_current else 1
        
        text_frame = tk.LabelFrame(parent, text='💬 피드백 내용', bg=bg_color, fg='#333', 
                                  font=self.font_manager.ui_font_bold,
                                  relief='flat', bd=1,
                                  highlightthickness=1,
                                  highlightbackground='#dee2e6',
                                  highlightcolor='#dee2e6')
        text_frame.pack(fill=tk.X, padx=12, pady=(0, 8))
        text_container = tk.Frame(text_frame, bg=bg_color)
        text_container.pack(fill=tk.X, padx=8, pady=6)
        # 텍스트 위젯 - 포커스 시 진한 회색 테두리
        # 🔥 다국어 지원 최적화 폰트 설정 (한글, 일본어, 중국어 등)
        unified_font_size = 12  # 안정적인 크기
        multilang_font = ('Noto Sans CJK KR', '맑은 고딕', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans')
        logger.debug(f"🌏 피드백 입력창 다국어 폰트: {multilang_font} {unified_font_size}px")
        
        text_widget = tk.Text(text_container, height=6, wrap=tk.WORD, 
                             font=(multilang_font, unified_font_size), 
                             relief='flat', bd=1,
                             highlightthickness=1,
                             highlightbackground='#dee2e6',
                             highlightcolor='#888888',
                             insertwidth=2,  # 🔥 커서 너비 고정
                             insertborderwidth=0,  # 🔥 커서 테두리 제거
                             insertofftime=300,  # 🔥 커서 깜빡임 조정
                             insertontime=600)   # 🔥 커서 표시 시간 조정
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 🔥 한글 조합 중 안정적인 표시를 위한 고급 설정
        try:
            # 일관된 폰트 렌더링을 위한 설정
            text_widget.configure(
                spacing1=2,  # 줄 위 간격 고정
                spacing2=1,  # 줄 사이 간격 고정  
                spacing3=2,  # 줄 아래 간격 고정
                selectborderwidth=0,  # 선택 테두리 제거
                selectforeground='black',  # 선택 시 글자색 고정
                selectbackground='lightblue'  # 선택 배경색 고정
            )
            # 태그 기반 일관된 폰트 적용
            text_widget.tag_configure('all', font=(stable_font, unified_font_size))
            text_widget.tag_add('all', '1.0', 'end')
            # IME 조합창 설정
            text_widget.tk.call('tk::imestatus', text_widget, 'on')
        except:
            pass
        text_scrollbar = tk.Scrollbar(text_container, orient=tk.VERTICAL, 
                                     command=text_widget.yview, width=24)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.configure(yscrollcommand=text_scrollbar.set)
        
        if item.get('feedback_text', ''):
            text_widget.insert('1.0', item['feedback_text'])
        
        # 업데이트 관리
        update_manager = {
            'timer_id': None,
            'last_content': item.get('feedback_text', ''),
            'is_composing': False
        }
        
        def safe_update():
            """안전한 텍스트 업데이트"""
            try:
                current_content = text_widget.get('1.0', tk.END).strip()
                if current_content != update_manager['last_content']:
                    item['feedback_text'] = current_content
                    update_manager['last_content'] = current_content
            except Exception as e:
                logger.debug(f"텍스트 업데이트 오류: {e}")
        
        def schedule_update(delay=300):
            """지연된 업데이트 스케줄링"""
            if update_manager['timer_id']:
                text_widget.after_cancel(update_manager['timer_id'])
            update_manager['timer_id'] = text_widget.after(delay, safe_update)
        
        def on_key_press(event):
            """키 입력 시 처리 - 폰트 일관성 유지"""
            schedule_update(300)
            # 🔥 한글 조합 중 폰트 일관성 유지
            try:
                text_widget.tag_add('all', '1.0', 'end')
                text_widget.tag_configure('all', font=(stable_font, unified_font_size))
            except:
                pass
        
        def on_key_release(event):
            """키 해제 시 처리"""
            schedule_update(200)
        
        def on_focus_in(event):
            """포커스 진입 시 - 카드 활성화 및 텍스트 테두리 진하게"""
            if index is not None and self.current_index != index:
                self.current_index = index
                self.update_card_borders()  # 🔥 테두리 업데이트 추가
                self.update_status()
            # 텍스트 위젯 테두리 진하게 (회색)
            try:
                text_widget.configure(highlightthickness=2)
            except:
                pass
        
        def on_focus_out(event):
            """포커스 벗어날 때 즉시 업데이트 및 테두리 원래대로"""
            if update_manager['timer_id']:
                text_widget.after_cancel(update_manager['timer_id'])
            safe_update()
            # 텍스트 위젯 테두리 원래대로
            try:
                text_widget.configure(highlightthickness=1)
            except:
                pass
        
        # 최적화된 이벤트 바인딩
        text_widget.bind('<KeyPress>', on_key_press)
        text_widget.bind('<KeyRelease>', on_key_release)
        text_widget.bind('<FocusIn>', on_focus_in)
        text_widget.bind('<FocusOut>', on_focus_out)
        
        # 🔥 텍스트 위젯 클릭 시 카드 활성화 및 텍스트 테두리 진하게
        def on_text_click(event):
            if index is not None and self.current_index != index:
                self.current_index = index
                self.update_card_borders()
                self.update_status()
            text_widget.focus_set()
            # 클릭 시 텍스트 테두리 진하게 (회색)
            try:
                text_widget.configure(highlightthickness=2)
            except:
                pass
        
        # 기본 이벤트들
        text_widget.bind('<Button-1>', on_text_click)
        
        # Delete/Backspace 정상 동작
        def handle_edit_key(event):
            schedule_update(100)
            return None
        
        text_widget.bind('<Delete>', handle_edit_key)
        text_widget.bind('<BackSpace>', handle_edit_key)

    def create_context_menu(self, widget, item):
        """우클릭 컨텍스트 메뉴 생성"""
        try:
            context_menu = tk.Menu(self.root, tearoff=0, font=self.font_manager.ui_font)
            
            can_undo = self.undo_manager.can_undo(item['id'])
            undo_text = "↶ 되돌리기" if can_undo else "↶ 되돌리기 (불가능)"
            context_menu.add_command(
                label=undo_text,
                command=self.handle_undo,
                state='normal' if can_undo else 'disabled'
            )
            
            context_menu.add_separator()
            
            context_menu.add_command(
                label="🧹 모든 주석 지우기",
                command=self.clear_current_annotations
            )
            
            context_menu.add_separator()
            
            context_menu.add_command(
                label="📝 이름 변경",
                command=self.rename_current
            )
            
            context_menu.add_command(
                label="🗑️ 삭제",
                command=self.handle_delete_key
            )
            
            def show_context_menu(event):
                try:
                    context_menu.tk_popup(event.x_root, event.y_root)
                finally:
                    context_menu.grab_release()
            
            widget.bind('<Button-3>', show_context_menu)
            
        except Exception as e:
            logger.error(f"컨텍스트 메뉴 생성 오류: {e}")

    def set_current_index_no_refresh(self, index):
        """현재 선택 인덱스 설정 (스크롤 위치 유지) - 최적화"""
        if self.current_index == index:
            return  # 이미 선택된 창이면 아무것도 하지 않음
        
        if 0 <= index < len(self.feedback_items):
            self.current_index = index
            self.clear_selection()  # 다른 항목 선택시 기존 선택 해제
            
            # 🔥 핵심! schedule_ui_refresh() 제거하고 scroll_to_card만 호출
            self.scroll_to_card(index)
            self.update_status()

    def scroll_to_card(self, index):
        """해당 카드가 스크롤 영역에서 보이도록 스크롤 이동 (중앙 정렬)"""
        try:
            card_widgets = [w for w in self.scrollable_frame.winfo_children() if hasattr(w, 'item_index')]
            for card in card_widgets:
                if getattr(card, 'item_index', None) == index:
                    self.main_canvas.update_idletasks()
                    y = card.winfo_y()
                    total_height = self.scrollable_frame.winfo_height()
                    canvas_height = self.main_canvas.winfo_height()
                    # 카드가 화면 중앙에 오도록 조정
                    y_center = max(0, y - (canvas_height // 2) + (card.winfo_height() // 2))
                    yview = y_center / max(1, total_height - canvas_height)
                    self.main_canvas.yview_moveto(yview)
                    break
        except Exception as e:
            logger.debug(f"스크롤 포커스 오류: {e}")

    def move_current_up(self):
        """현재 항목을 위로 이동"""
        if self.current_index > 0:
            self.feedback_items[self.current_index], self.feedback_items[self.current_index - 1] = \
                self.feedback_items[self.current_index - 1], self.feedback_items[self.current_index]
            self.current_index -= 1
            self.schedule_ui_refresh()
            self.update_status()
            self.root.after(100, self.update_card_borders)

    def move_current_down(self):
        """현재 항목을 아래로 이동"""
        if self.current_index < len(self.feedback_items) - 1:
            self.feedback_items[self.current_index], self.feedback_items[self.current_index + 1] = \
                self.feedback_items[self.current_index + 1], self.feedback_items[self.current_index]
            self.current_index += 1
            self.schedule_ui_refresh()
            self.update_status()
            self.root.after(100, self.update_card_borders)

    def delete_current(self):
        """현재 항목 삭제"""
        try:
            if not self.feedback_items:
                return

            # 주석이 선택된 상태에서는 확인 메시지 없이 삭제
            if self.selected_annotations:
                deleted_item = self.feedback_items.pop(self.current_index)
                self.undo_manager.clear_history(deleted_item['id'])
                
                if self.current_index >= len(self.feedback_items):
                    self.current_index = max(0, len(self.feedback_items) - 1)
                self.clear_selection()
                self.schedule_ui_refresh()
                self.update_status()
                return

            # 주석이 선택되지 않은 상태에서는 확인 메시지 표시
            if messagebox.askyesno('삭제 확인', '현재 선택된 피드백을 삭제하시겠습니까?'):
                deleted_item = self.feedback_items.pop(self.current_index)
                self.undo_manager.clear_history(deleted_item['id'])
                
                if self.current_index >= len(self.feedback_items):
                    self.current_index = max(0, len(self.feedback_items) - 1)
                self.clear_selection()
                self.schedule_ui_refresh()
                self.update_status()

        except Exception as e:
            logger.error(f"프로젝트 삭제 오류: {e}")
            messagebox.showerror('삭제 오류', f'삭제 중 오류가 발생했습니다: {str(e)}')

    def save_project_to_file(self, file_path, show_popup=True):
        """파일로 프로젝트 저장"""
        try:
            progress = AdvancedProgressDialog(self.root, "프로젝트 저장", "프로젝트를 저장하고 있습니다...", auto_close_ms=1000)
            
            try:
                progress.update(10, "프로젝트 정보 수집 중...")
                
                project_data = {
                    'title': self.project_title.get(),
                    'to': self.project_to.get(),
                                    'from': self.project_from.get(),
                'description': self.project_description.get(),
                'footer': self.project_footer.get(),
                'footer_first_page_only': self.footer_first_page_only.get(),
                    'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'version': VERSION,
                    'build_date': BUILD_DATE,
                    'feedback_items': []
                }
                
                progress.update(20, "이미지 데이터 변환 중...")
                
                for i, item in enumerate(self.feedback_items):
                    buffer = io.BytesIO()
                    save_kwargs = {'format': 'PNG', 'optimize': True}
                    if item['image'].mode == 'RGB':
                        save_kwargs.update({'format': 'JPEG', 'quality': 85, 'optimize': True})
                    
                    item['image'].save(buffer, **save_kwargs)
                    image_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    
                    project_data['feedback_items'].append({
                        'id': item['id'],
                        'name': item['name'],
                        'image': image_b64,
                        'feedback_text': item['feedback_text'],
                        'annotations': item.get('annotations', []),
                        'timestamp': item['timestamp'],
                        'source_type': item.get('source_type', '알 수 없음')
                    })
                    
                    progress.update(20 + (i / len(self.feedback_items)) * 60, 
                                  f"이미지 처리 중... ({i+1}/{len(self.feedback_items)})")

                progress.update(80, "파일 저장 중...")
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(project_data, f, ensure_ascii=False, indent=2)
                
                progress.update(100, "완료!")
                progress.close()
                
                if show_popup:
                    messagebox.showinfo(
                         '저장 완료',
                        f'프로젝트가 저장되었습니다:\n{Path(file_path).name}\n\n항목 수: {len(self.feedback_items)}개'
                 )
            
            finally:
                try:
                    progress.close()
                except:
                    pass
            
        except PermissionError as e:
            logger.error(f"권한 오류: {e}")
            messagebox.showerror('권한 오류', 
                               '파일 저장 권한이 없습니다.\n다른 위치에 저장하거나 관리자 권한으로 실행해주세요.')
        except Exception as e:
            logger.error(f"파일 저장 오류: {e}")
            messagebox.showerror('저장 오류', f'파일 저장 중 오류가 발생했습니다: {str(e)}')

    def load_project(self):
        """프로젝트 불러오기"""
        try:
            if self.feedback_items:
                result = messagebox.askyesnocancel('프로젝트 불러오기', 
                                                 '현재 작업 중인 프로젝트가 있습니다.\n저장하고 불러오시겠습니까?')
                if result is None:
                    return
                elif result:
                    self.save_project()
            
            file_path = filedialog.askopenfilename(
                filetypes=[('JSON 파일', '*.json'), ('모든 파일', '*.*')]
            )
            
            if file_path:
                self.load_project_from_file(file_path)
                
        except Exception as e:
            logger.error(f"프로젝트 불러오기 오류: {e}")
            messagebox.showerror('불러오기 오류', f'불러오기 중 오류가 발생했습니다: {str(e)}')

    def load_project_from_file(self, file_path):
        """파일에서 프로젝트 불러오기"""
        try:
            progress = AdvancedProgressDialog(self.root, "프로젝트 불러오기", "프로젝트를 불러오고 있습니다...")
            
            try:
                progress.update(10, "파일 읽기 중...")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                
                progress.update(20, "프로젝트 정보 로드 중...")
                
                self.project_title.set(project_data.get('title', '피드백 캔버스 프로젝트'))
                self.project_to.set(project_data.get('to', ''))
                self.project_from.set(project_data.get('from', ''))
                self.project_description.set(project_data.get('description', ''))
                self.project_footer.set(project_data.get('footer', '피드백 캔버스'))
                self.footer_first_page_only.set(project_data.get('footer_first_page_only', False))
                
                progress.update(30, "기존 데이터 정리 중...")
                
                self.feedback_items.clear()
                self.undo_manager.clear_all()
                self.clear_selection()
                
                progress.update(40, "피드백 항목 로드 중...")
                
                feedback_items = project_data.get('feedback_items', [])
                for i, item_data in enumerate(feedback_items):
                    try:
                        image_data = base64.b64decode(item_data['image'])
                        image = Image.open(io.BytesIO(image_data))
                        
                        image = self.optimize_image(image)
                        
                        item_data['image'] = image
                        self.feedback_items.append(item_data)
                        
                        self.undo_manager.save_state(item_data['id'], item_data.get('annotations', []))
                        
                        progress.update(40 + (i / len(feedback_items)) * 50, 
                                      f"이미지 로드 중... ({i+1}/{len(feedback_items)})")
                        
                    except Exception as e:
                        logger.warning(f"이미지 로드 실패: {e}")
                        continue
                
                progress.update(90, "UI 업데이트 중...")
                
                self.current_index = 0
                self.schedule_ui_refresh()
                self.update_status()
                
                progress.update(100, "완료!")
                progress.close()
                
                logger.info(f"프로젝트 로드 완료: {file_path}")
                
                loaded_version = project_data.get('version', '알 수 없음')
                version_info = f"\n버전: {loaded_version}" if loaded_version != VERSION else ""
                
                messagebox.showinfo('불러오기 완료', 
                                  f'프로젝트가 로드되었습니다.\n\n파일: {Path(file_path).name}\n피드백 수: {len(self.feedback_items)}개{version_info}')
                
            finally:
                try:
                    progress.close()
                except:
                    pass
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
            messagebox.showerror('파일 오류', '올바르지 않은 프로젝트 파일입니다.\nJSON 형식이 손상되었습니다.')
        except Exception as e:
            logger.error(f"프로젝트 로드 오류: {e}")
            messagebox.showerror('불러오기 오류', f'프로젝트 로드 중 오류가 발생했습니다: {str(e)}')

    def show_pdf_info_dialog(self):
        """PDF 정보 입력 다이얼로그 표시"""
        try:
            if not REPORTLAB_AVAILABLE:
                messagebox.showerror('오류', 
                                   'ReportLab 모듈이 필요합니다.\n\n설치 방법:\n1. 명령 프롬프트(CMD)를 관리자 권한으로 실행\n2. pip install reportlab 입력')
                return
            
            if not self.feedback_items:
                messagebox.showwarning('PDF 생성', '생성할 피드백이 없습니다.')
                return
            
            # PDF 정보 입력 다이얼로그 생성
            pdf_dialog = PDFInfoDialog(self.root, self)
            
            # 🔥 PDF 다이얼로그에 아이콘 설정 (생성 후 즉시 적용)
            if hasattr(pdf_dialog, 'dialog') and pdf_dialog.dialog:
                try:
                    setup_window_icon(pdf_dialog.dialog)
                    print("[PDF 다이얼로그] ✅ 아이콘 설정 성공!")
                except Exception as e:
                    print(f"[PDF 다이얼로그] ❌ 아이콘 설정 실패: {e}")
            
        except Exception as e:
            logger.error(f"PDF 정보 다이얼로그 오류: {e}")
            messagebox.showerror('오류', f'PDF 정보 창을 열 수 없습니다: {str(e)}')

    def start_pdf_generation(self):
        """PDF 생성 시작 - 페이지 모드 고려"""
        try:
            # 디스크 공간 확인
            free_space = self.system_monitor.get_disk_space(os.getcwd())
            estimated_size = len(self.feedback_items) * 8
            if free_space < estimated_size + 100:
                messagebox.showwarning('디스크 공간 부족', 
                                     f'디스크 여유 공간이 부족할 수 있습니다.\n예상 크기: {estimated_size}MB\n여유 공간: {free_space:.1f}MB')

            current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            project_title = self.project_title.get().strip()
            
            # 🔥 PDF 모드에 따른 파일명 설정
            mode_suffix = ""
            if hasattr(self, 'pdf_page_mode') and self.pdf_page_mode == 'adaptive':
                mode_suffix = "_적응형"
            
            if project_title:
                default_filename = f"{project_title}_고화질피드백{mode_suffix}_{current_time}.pdf"
            else:
                default_filename = f"고화질피드백{mode_suffix}_{current_time}.pdf"

            file_path = filedialog.asksaveasfilename(
                defaultextension='.pdf',
                filetypes=[('PDF 파일', '*.pdf'), ('모든 파일', '*.*')],
                initialfile=default_filename
            )
            
            if not file_path:
                return
            
            # 파일 사용 가능성 확인
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'a'):
                        pass
                except PermissionError:
                    messagebox.showerror('PDF 저장 오류', 
                                       f'파일이 다른 프로그램에서 사용 중입니다.\n{Path(file_path).name} 파일을 닫고 다시 시도해주세요.')
                    return
            
            # 🔥 페이지 모드에 따라 다른 생성 방법 사용
            if hasattr(self, 'pdf_page_mode') and self.pdf_page_mode == 'adaptive':
                self.export_adaptive_pdf_async(file_path)
            else:
                self.export_pdf_async_internal(file_path)  # 기존 A4 방식
            
        except Exception as e:
            logger.error(f"PDF 생성 시작 오류: {e}")
            messagebox.showerror('오류', f'PDF 생성 시작 중 오류가 발생했습니다: {str(e)}')

    def create_adaptive_pdf_page(self, item):
        """이미지 크기에 맞는 PDF 페이지 크기 계산 - 완전 재설계 (레이아웃 일관성 보장)"""
        try:
            img_width = item['image'].width
            img_height = item['image'].height
            
            # 🔥 A4 크기 정의 (포인트 단위)
            A4_PORTRAIT_WIDTH = 595   # A4 세로형 너비
            A4_PORTRAIT_HEIGHT = 842  # A4 세로형 높이  
            A4_LANDSCAPE_WIDTH = 842  # A4 가로형 너비
            A4_LANDSCAPE_HEIGHT = 595 # A4 가로형 높이
            
            # 🔥 이미지 비율 분석
            img_ratio = img_width / img_height
            
            logger.info(f"🔥 적응형 레이아웃 계산 시작: 이미지({img_width}×{img_height}), 비율({img_ratio:.3f})")
            
            # 🔥 최소 300 DPI 보장
            min_dpi = 300
            current_dpi = self.pdf_quality.get()
            effective_dpi = max(min_dpi, current_dpi)
            
            # 🔥 이미지 타입별 설정 (웹툰/가로형/세로형)
            if img_ratio < 0.65:  # 웹툰형
                target_orientation = "세로 긴 이미지(웹툰)"
                margin_points = 5 * 72 / 25.4  # 5mm 적절한 여백 (A4 최소 크기 고려)
                effective_dpi = max(400, effective_dpi)  # 웹툰 고해상도
                logger.info(f"🔥 웹툰 모드: 적절한여백({margin_points:.1f}pt), 고해상도({effective_dpi}DPI)")
            elif img_ratio > 1.3:  # 가로형
                target_orientation = "가로형"
                margin_points = 5 * 72 / 25.4  # 5mm (여백 최소화)
                logger.info(f"🔥 가로형 모드: 여백최소화({margin_points:.1f}pt)")
            else:  # 세로형
                target_orientation = "세로형"
                margin_points = 5 * 72 / 25.4  # 5mm (여백 최소화)
                logger.info(f"🔥 세로형 모드: 여백최소화({margin_points:.1f}pt)")
            
            # 🔥 1단계: 이미지 영역 크기 확정 (DPI 기준)
            image_width_pt = (img_width / effective_dpi) * 72
            image_height_pt = (img_height / effective_dpi) * 72
            
            logger.info(f"🔥 이미지 영역 확정: {image_width_pt:.1f} x {image_height_pt:.1f}pt")
            
            # 🔥 2단계: 텍스트 영역 크기 확정
            feedback_text = item.get('feedback_text', '').strip()
            text_area_height = 0
            text_gap = 0
        
            if feedback_text:
                # 텍스트 영역 크기 정확 계산
                try:
                    korean_font = self.font_manager.register_pdf_font()
                    temp_canvas = pdf_canvas.Canvas("temp.pdf", pagesize=A4)
                    
                    # 텍스트가 들어갈 너비는 이미지 너비와 동일하게
                    text_width = image_width_pt
                    if target_orientation == "세로 긴 이미지(웹툰)":
                        # 웹툰은 내부 여백 극소화
                        max_text_width = text_width - 16  # 좌우 8pt씩
                    else:
                        max_text_width = text_width - 40  # 좌우 20pt씩
                    
                    # 텍스트 줄 수 계산
                    text_lines = self._wrap_text_for_pdf(feedback_text, max_text_width, korean_font, 11, temp_canvas)
                    
                    # 텍스트 영역 높이 계산
                    line_height = 18
                    title_space = 30
                    bottom_padding = 15
                    text_area_height = len(text_lines) * line_height + title_space + bottom_padding
                    
                    # 텍스트 간격
                    text_gap = 10 if target_orientation == "세로 긴 이미지(웹툰)" else 15
                    
                    logger.info(f"📝 텍스트 영역 확정: {len(text_lines)}줄 → {text_area_height:.1f}pt, 간격:{text_gap}pt")
                    
                except Exception as e:
                    logger.warning(f"텍스트 영역 계산 오류: {e}, 폴백 사용")
                    text_length = len(feedback_text)
                    if text_length < 100:
                        text_area_height = 80
                    elif text_length < 300:
                        text_area_height = 120
                    elif text_length < 600:
                        text_area_height = 160
                    else:
                        text_area_height = 200
                    text_gap = 10 if target_orientation == "세로 긴 이미지(웹툰)" else 15
        
            # 🔥 3단계: 고정 레이아웃으로 페이지 크기 계산
            # 레이아웃: [상단여백] + [이미지] + [텍스트간격] + [텍스트영역] + [하단여백]
            
            page_width = image_width_pt + (margin_points * 2)  # 좌우 여백
            page_height = margin_points + image_height_pt + text_gap + text_area_height + margin_points  # 상하 여백 + 이미지 + 간격 + 텍스트
            
            logger.info(f"🔥 고정 레이아웃 페이지 크기: {page_width:.1f} x {page_height:.1f}pt")
            
            # 🔥 4단계: A4 최소 크기 보장 강화 (모든 타입)
            if target_orientation == "가로형":
                # 🔥 가로형: A4 가로형 강제 적용 + 여백 최소화 + 중앙 배치
                page_width = A4_LANDSCAPE_WIDTH  # A4 가로형 너비 강제
                if page_height < A4_LANDSCAPE_HEIGHT:
                    page_height = A4_LANDSCAPE_HEIGHT  # A4 가로형 높이 최소 보장
                logger.info(f"📄 A4 가로형 강제 적용: {page_width:.0f}x{page_height:.0f}pt (여백최소화+중앙배치)")
                    
            elif target_orientation == "세로형":
                # 🔥 세로형: A4 세로형 강제 적용 + 여백 최소화 + 중앙 배치
                page_width = A4_PORTRAIT_WIDTH   # A4 세로형 너비 강제
                if page_height < A4_PORTRAIT_HEIGHT:
                    page_height = A4_PORTRAIT_HEIGHT  # A4 세로형 높이 최소 보장
                logger.info(f"📄 A4 세로형 강제 적용: {page_width:.0f}x{page_height:.0f}pt (여백최소화+중앙배치)")
            
            else:  # 웹툰형
                # 🔥 웹툰도 A4 세로형 최소 너비 보장 (너무 작아지지 않도록)
                min_width = A4_PORTRAIT_WIDTH * 0.6  # A4 세로형 너비의 60% 최소 보장
                max_height = A4_PORTRAIT_HEIGHT * 30  # 최대 높이 더욱 확장 (웹툰 잘림 완전 방지)
                
                if page_width < min_width:
                    # 너비가 너무 작으면 최소 너비로 확대하고 이미지와 여백도 비례 확대
                    scale_factor = min_width / page_width
                    page_width = min_width
                    page_height *= scale_factor
                    image_width_pt *= scale_factor
                    image_height_pt *= scale_factor
                    margin_points *= scale_factor
                    logger.info(f"📄 웹툰 A4 최소 너비 적용: 확대율 {scale_factor:.2f} (너비 {min_width:.0f}pt)")
                    
                if page_height > max_height:
                    page_height = max_height
                    logger.info(f"📄 웹툰 최대 높이 제한: {max_height}pt")
                    
                logger.info(f"🔥 웹툰 A4 기준 최소 크기: 좌우 각 {margin_points*25.4/72:.1f}mm 여백")
            
            # 🔥 최대 크기 제한 (포스터급 크기 방지) - 웹툰 예외 처리
            max_width = 42 * 72   # A0 크기 정도
            if target_orientation == "세로 긴 이미지(웹툰)":
                max_height = 120 * 72  # 웹툰용 매우 긴 높이 허용 (기존 60 → 120)
                logger.info(f"🔥 웹툰 전용 최대 높이: {max_height:.0f}pt ({max_height/72:.1f}인치)")
            else:
                max_height = 60 * 72  # 일반 이미지용 배너 크기
            
            page_width = min(page_width, max_width)
            page_height = min(page_height, max_height)
            
            # 🔥 5단계: 레이아웃 정보 저장 (렌더링에서 사용)
            # A4 강제 적용 시 이미지 크기 재조정 (중앙 배치를 위해)
            if target_orientation in ["가로형", "세로형"]:
                # 🔥 A4 페이지에서 여백을 제외한 실제 사용 가능 영역 계산 (겹침 방지)
                available_width = page_width - (margin_points * 2)
                
                # 🔥 텍스트 영역을 먼저 확보하고 남은 공간을 이미지에 할당 (겹침 완전 방지)
                # 안전한 간격 추가: 기본 간격의 2배 + 추가 패딩
                safe_gap = max(text_gap * 2, 30)  # 최소 30pt 안전 간격
                reserved_for_text = text_area_height + safe_gap + (margin_points * 2)  # 텍스트 + 안전간격 + 상하여백
                available_height_for_image = page_height - reserved_for_text
                
                # 🔥 이미지 영역이 너무 작아지는 것 방지 (최소 높이 보장)
                min_image_height = page_height * 0.35  # 페이지 높이의 35%로 조정 (40% → 35%)
                if available_height_for_image < min_image_height:
                    available_height_for_image = min_image_height
                    # 텍스트 영역을 축소해서 맞춤
                    remaining_height = page_height - available_height_for_image - safe_gap - (margin_points * 2)
                    if remaining_height > 50:  # 최소 텍스트 영역 보장
                        text_area_height = remaining_height
                        logger.warning(f"🔧 텍스트 영역 축소: {text_area_height:.0f}pt (이미지 공간 확보)")
                    else:
                        # 텍스트 영역이 너무 작으면 페이지 높이를 늘림
                        needed_height = available_height_for_image + safe_gap + 80 + (margin_points * 2)  # 최소 텍스트 80pt
                        if needed_height > page_height:
                            page_height = needed_height
                            text_area_height = 80
                            logger.warning(f"🔧 페이지 높이 확장: {page_height:.0f}pt (겹침 완전 방지)")
                
                # 이미지 비율 유지하면서 사용 가능 영역에 맞게 크기 조정
                scale_x = available_width / image_width_pt
                scale_y = available_height_for_image / image_height_pt
                scale_factor = min(scale_x, scale_y)  # 비율 유지
                
                # 조정된 이미지 크기
                adjusted_image_width_pt = image_width_pt * scale_factor
                adjusted_image_height_pt = image_height_pt * scale_factor
                
                logger.info(f"🎯 A4 겹침방지 최적화:")
                logger.info(f"   이미지 영역: {available_width:.0f}x{available_height_for_image:.0f}pt")
                logger.info(f"   이미지 크기: {image_width_pt:.0f}x{image_height_pt:.0f} → {adjusted_image_width_pt:.0f}x{adjusted_image_height_pt:.0f}pt (배율 {scale_factor:.2f})")
                logger.info(f"   텍스트 영역: {text_area_height:.0f}pt (간격 {text_gap:.0f}pt)")
                
                # 레이아웃에 조정된 값 저장
                self.adaptive_layout = {
                    'page_width': page_width,
                    'page_height': page_height,
                    'margin_points': margin_points,
                    'image_width_pt': adjusted_image_width_pt,
                    'image_height_pt': adjusted_image_height_pt,
                    'text_area_height': text_area_height,
                    'text_gap': text_gap,
                    'safe_gap': safe_gap,  # 안전한 간격 정보 추가
                    'orientation': target_orientation,
                    'effective_dpi': effective_dpi,
                    'original_size': (img_width, img_height),
                    'scale_factor': scale_factor,  # 스케일 팩터 추가
                    'available_image_height': available_height_for_image  # 이미지 영역 높이 추가
                }
            else:
                # 🔥 웹툰: 텍스트 영역 보장 및 최적화
                # 웹툰에서도 텍스트 영역이 충분히 확보되도록 검증
                min_text_height = 100  # 최소 텍스트 영역 높이
                if text_area_height < min_text_height and feedback_text:
                    text_area_height = min_text_height
                    logger.info(f"🔧 웹툰 최소 텍스트 영역 보장: {text_area_height:.0f}pt")
                elif text_area_height == 0 and feedback_text:
                    # 텍스트가 있는데 영역이 0인 경우 최소 영역 할당
                    text_area_height = min_text_height
                    text_gap = 10
                    # 페이지 높이도 다시 계산해서 텍스트 영역 반영
                    page_height = margin_points + image_height_pt + text_gap + text_area_height + margin_points
                    logger.warning(f"🔧 웹툰 텍스트 영역 복구: {text_area_height:.0f}pt, 페이지 높이 재계산: {page_height:.0f}pt")
                
                # 웹툰도 안전한 간격 적용
                webtoon_safe_gap = max(text_gap * 2, 30) if text_gap > 0 else 30
                
                # 웹툰은 기존 방식 유지하되 텍스트 영역 개선
                self.adaptive_layout = {
                    'page_width': page_width,
                    'page_height': page_height,
                    'margin_points': margin_points,
                    'image_width_pt': image_width_pt,
                    'image_height_pt': image_height_pt,
                    'text_area_height': text_area_height,
                    'text_gap': text_gap,
                    'safe_gap': webtoon_safe_gap,  # 웹툰용 안전한 간격 추가
                    'orientation': target_orientation,
                    'effective_dpi': effective_dpi,
                    'original_size': (img_width, img_height)
                }
                
                logger.info(f"🔥 웹툰 레이아웃 확정:")
                logger.info(f"   페이지: {page_width:.0f}x{page_height:.0f}pt")
                logger.info(f"   이미지: {image_width_pt:.0f}x{image_height_pt:.0f}pt")
                logger.info(f"   텍스트: {text_area_height:.0f}pt (표시보장)")
            
            logger.info(f"🎯 최종 레이아웃 확정:")
            logger.info(f"   페이지: {page_width:.0f} x {page_height:.0f}pt ({page_width/72:.1f}\" x {page_height/72:.1f}\")")
            logger.info(f"   이미지: {image_width_pt:.0f} x {image_height_pt:.0f}pt ({effective_dpi} DPI)")
            logger.info(f"   텍스트: {text_area_height:.0f}pt (간격 {text_gap}pt)")
            logger.info(f"   여백: {margin_points:.1f}pt ({margin_points*25.4/72:.1f}mm)")
            
            return page_width, page_height
            
        except Exception as e:
            logger.error(f"적응형 페이지 크기 계산 오류: {e}")
            return A4  # 폴백

    def export_adaptive_pdf_async(self, file_path):
        """적응형 PDF 비동기 내보내기"""
        try:
            progress = AdvancedProgressDialog(self.root, "적응형 PDF 생성", 
                                            "이미지 크기에 맞춘 PDF를 생성하고 있습니다...", 
                                            cancelable=True)
            
            def pdf_worker():
                try:
                    progress.update(10, "PDF 생성 준비 중...")
                    
                    # 가독성 모드 설정 (다이얼로그 결과에서 가져옴)
                    readability_mode = getattr(self, 'pdf_readability_mode', False)
                    logger.info(f"PDF 가독성 모드: {readability_mode}")
                    # 가독성 모드 초기화 (항상 False로 시작)
                    self.pdf_generator.set_readability_mode(False)
                    if readability_mode:
                        self.pdf_generator.set_readability_mode(True)
                        progress.update(15, "가독성 모드가 활성화되었습니다...")
                        logger.info("PDF 생성기에 가독성 모드 설정됨")
                    else:
                        logger.info("PDF 생성기 가독성 모드 비활성화됨")
                    
                    c = pdf_canvas.Canvas(file_path, pagesize=A4)
                    c.setTitle(self.project_title.get())
                    
                    # 🔥 첫장 제외하기 설정 확인
                    skip_title = getattr(self, 'skip_title_page', False)
                    
                    if not skip_title:
                        # 제목 페이지 (A4 고정)
                        korean_font = self.font_manager.register_pdf_font()
                        self.create_pdf_title_page(c, A4[0], A4[1], korean_font)
                    
                    total_items = len(self.feedback_items)
                    for index, item in enumerate(self.feedback_items):
                        progress.update(
                            int(10 + (index / total_items * 80)),
                            f"피드백 {index + 1}/{total_items} 처리 중..."
                        )
                        if progress.canceled:
                            return {'cancelled': True}
                        
                        # 🔥 첫 번째 페이지인지 확인 (제목 페이지 제외 시 showPage 호출 안함)
                        if index == 0 and skip_title:
                            # 첫 번째 피드백이면서 제목 페이지를 제외하는 경우 showPage 호출 안함
                            pass
                        else:
                            c.showPage()
                        
                        # 🔥 이미지 크기에 맞는 페이지 크기 설정
                        page_width, page_height = self.create_adaptive_pdf_page(item)
                        c.setPageSize((page_width, page_height))
                        
                        # 🔥 이미지 크기에 맞춤 PDF에서도 투명도 지원 페이지 생성
                        try:
                            # 투명도가 있는 이미지 주석 확인
                            all_annotations = item.get('annotations', [])
                            image_annotations = [ann for ann in all_annotations if ann.get('type') == 'image']
                            
                            # 투명도가 있는 이미지 주석 확인
                            has_transparent_images = any(
                                ann.get('opacity', 100) < 100 
                                for ann in image_annotations
                            )
                            
                            logger.info(f"적응형 PDF - 주석 분석: 전체 {len(all_annotations)}개, 이미지 {len(image_annotations)}개, 투명도 있음: {has_transparent_images}")
                            
                            # 🔥 적응형 모드 전용 페이지 생성
                            logger.info("적응형 PDF - 최적화된 레이아웃 사용")
                            self.pdf_generator._adaptive_pdf_page(c, item, index, page_width, page_height)
                                
                        except Exception as e:
                            logger.warning(f"적응형 PDF 생성 실패: {e}")
                            self.pdf_generator._adaptive_pdf_page(c, item, index, page_width, page_height)
                    
                    progress.update(95, "PDF 파일 저장 중...")
                    c.save()
                    
                    return {'success': True, 'file_path': file_path}
                    
                except Exception as e:
                    logger.error(f"적응형 PDF 생성 작업 오류: {e}")
                    return {'error': str(e)}
            
            def on_pdf_complete(result):
                progress.close()
                
                if 'cancelled' in result:
                    self.update_status_message("PDF 생성이 취소되었습니다")
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception:
                        pass
                    return
                
                if 'error' in result:
                    messagebox.showerror('PDF 생성 오류', 
                                       f'적응형 PDF를 생성하는 중 오류가 발생했습니다:\n{result["error"]}')
                    return
                
                if result.get('success'):
                    self.update_status_message("적응형 PDF 파일이 생성되었습니다")
                    if sys.platform == 'win32':
                        os.startfile(file_path)
                    elif sys.platform == 'darwin':
                        subprocess.run(['open', file_path])
                    else:
                        subprocess.run(['xdg-open', file_path])
            
            def on_pdf_error(error):
                progress.close()
                logger.error(f"적응형 PDF 생성 중 오류 발생: {error}")
                messagebox.showerror('오류', f'적응형 PDF 생성 중 오류가 발생했습니다:\n{str(error)}')
            
            progress.set_cancel_callback(lambda: self.update_status_message("PDF 생성 취소 중..."))
            self.task_manager.submit_task(pdf_worker, callback=on_pdf_complete, 
                                        error_callback=on_pdf_error)
            
        except Exception as e:
            logger.error(f"적응형 PDF 생성 시작 오류: {e}")
            messagebox.showerror('오류', f'적응형 PDF 생성을 시작할 수 없습니다: {str(e)}')

    def export_pdf_async_internal(self, file_path):
        """내부 PDF 생성 메서드"""
        try:
            progress = AdvancedProgressDialog(self.root, "고화질 PDF 생성", 
                                            f"{self.pdf_quality.get()} DPI 고화질 PDF를 생성하고 있습니다...", 
                                            cancelable=True)
            
            def pdf_worker():
                try:
                    progress.update(10, "PDF 생성 준비 중...")
                    
                    # 가독성 모드 설정 (다이얼로그 결과에서 가져옴)
                    readability_mode = getattr(self, 'pdf_readability_mode', False)
                    logger.info(f"PDF 가독성 모드: {readability_mode}")
                    # 가독성 모드 초기화 (항상 False로 시작)
                    self.pdf_generator.set_readability_mode(False)
                    if readability_mode:
                        self.pdf_generator.set_readability_mode(True)
                        progress.update(15, "가독성 모드가 활성화되었습니다...")
                        logger.info("PDF 생성기에 가독성 모드 설정됨")
                    else:
                        logger.info("PDF 생성기 가독성 모드 비활성화됨")
                    
                    # A4 크기 설정 (단위: 포인트)
                    page_width, page_height = A4
                    
                    # PDF 생성
                    c = pdf_canvas.Canvas(file_path, pagesize=A4)
                    c.setTitle(self.project_title.get())
                    
                    # 🔥 첫장 제외하기 설정 확인
                    skip_title = getattr(self, 'skip_title_page', False)
                    
                    if not skip_title:
                        # 제목 페이지 생성
                        self.create_pdf_title_page(c, page_width, page_height, self.font_manager.register_pdf_font())
                    
                    total_items = len(self.feedback_items)
                    for index, item in enumerate(self.feedback_items):
                        progress.update(
                            int(10 + (index / total_items * 80)),
                            f"피드백 {index + 1}/{total_items} 처리 중..."
                        )
                        if progress.canceled:
                            return {'cancelled': True}
                        
                        # 🔥 첫 번째 페이지인지 확인 (제목 페이지 제외 시 showPage 호출 안함)
                        if index == 0 and skip_title:
                            # 첫 번째 피드백이면서 제목 페이지를 제외하는 경우 showPage 호출 안함
                            pass
                        else:
                            # 새 페이지 생성
                            c.showPage()
                        
                        try:
                            # 🔥 투명도 지원을 위한 개선된 방식 선택
                            all_annotations = item.get('annotations', [])
                            image_annotations = [ann for ann in all_annotations if ann.get('type') == 'image']
                            
                            # 투명도가 있는 이미지 주석 확인
                            has_transparent_images = any(
                                ann.get('opacity', 100) < 100 
                                for ann in image_annotations
                            )
                            
                            logger.info(f"주석 분석: 전체 {len(all_annotations)}개, 이미지 {len(image_annotations)}개, 투명도 있음: {has_transparent_images}")
                            
                            # 🔥 투명도가 있는 경우 PNG 합성 방식 사용
                            if has_transparent_images:
                                logger.info("투명도 감지: PNG 합성 방식 사용")
                                self.pdf_generator.create_transparent_pdf_page(c, item, index, page_width, page_height)
                            else:
                                # 투명도가 없는 경우 기존 방식 사용
                                if len(image_annotations) > 0:
                                    logger.info("이미지 주석 감지: 고품질 합성 모드 사용")
                                    self.pdf_generator._fallback_pdf_page(c, item, index, page_width, page_height)
                                else:
                                    logger.info("이미지 주석 없음: 벡터 모드 사용")
                                    self.pdf_generator.create_vector_pdf_page(c, item, index, page_width, page_height)
                                    
                        except Exception as e:
                            logger.warning(f"PDF 생성 실패, 대체 모드로 전환: {e}")
                            # 실패 시 기본 폴백
                            self.pdf_generator._fallback_pdf_page(c, item, index, page_width, page_height)
                    
                    progress.update(95, "PDF 파일 저장 중...")
                    c.save()
                    
                    return {'success': True, 'file_path': file_path}
                    
                except Exception as e:
                    logger.error(f"PDF 생성 작업 오류: {e}")
                    return {'error': str(e)}
            
            def on_pdf_complete(result):
                progress.close()
                
                if 'cancelled' in result:
                    self.update_status_message("PDF 생성이 취소되었습니다")
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception:
                        pass
                    return
                
                if 'error' in result:
                    messagebox.showerror('PDF 생성 오류', 
                                       f'PDF를 생성하는 중 오류가 발생했습니다:\n{result["error"]}')

 
                if result.get('success'):
                    self.update_status_message("PDF 파일이 생성되었습니다")
                    if sys.platform == 'win32':
                        os.startfile(file_path)
                    elif sys.platform == 'darwin':
                        subprocess.run(['open', file_path])
                    else:
                        subprocess.run(['xdg-open', file_path])
            
            def on_pdf_error(error):
                progress.close()
                logger.error(f"PDF 생성 중 오류 발생: {error}")
                messagebox.showerror('오류', f'PDF 생성 중 오류가 발생했습니다:\n{str(error)}')
            
            progress.set_cancel_callback(lambda: self.update_status_message("PDF 생성 취소 중..."))
            self.task_manager.submit_task(pdf_worker, callback=on_pdf_complete, 
                                        error_callback=on_pdf_error)
            
        except Exception as e:
            logger.error(f"PDF 생성 시작 오류: {e}")
            messagebox.showerror('오류', f'PDF 생성을 시작할 수 없습니다: {str(e)}')

    def create_pdf_title_page(self, c, width, height, korean_font):
        """PDF 제목 페이지 생성"""
        try:
            # 제목 (상단 25% 위치)
            c.setFont(korean_font, 24)
            title_text = self.project_title.get()
            text_width = c.stringWidth(title_text, korean_font, 24)
            c.drawString((width - text_width) / 2, height * 0.75, title_text)
            
            # 프로젝트 정보 (중앙 영역)
            info_start_y = height * 0.65
            c.setFont(korean_font, 12)
            
            if self.project_to.get():
                to_text = f"수신: {self.project_to.get()}"
                to_width = c.stringWidth(to_text, korean_font, 12)
                c.drawString((width - to_width) / 2, info_start_y, to_text)
                info_start_y -= 30
            
            if self.project_from.get():
                from_text = f"발신: {self.project_from.get()}"
                from_width = c.stringWidth(from_text, korean_font, 12)
                c.drawString((width - from_width) / 2, info_start_y, from_text)
                info_start_y -= 30
            
            # 설명 필드 (중앙 하단)
            description = self.project_description.get().strip()
            if description:
                c.setFont(korean_font, 11)
                description_lines = self.wrap_text_for_pdf(description, width - 120, korean_font, 11, c)
                
                desc_y = height * 0.4
                for line in description_lines:
                    line_width = c.stringWidth(line, korean_font, 11)
                    c.drawString((width - line_width) / 2, desc_y, line)
                    desc_y -= 20
            
            # 피드백 개수 (하단)
            c.setFont(korean_font, 11)
            count_text = f"총 {len(self.feedback_items)}개 피드백"
            count_width = c.stringWidth(count_text, korean_font, 11)
            c.drawString((width - count_width) / 2, height * 0.25, count_text)
            
            # 서명 (하단 가운데) - 첫 장만 출력 옵션 지원
            footer_text = self.project_footer.get().strip()
            if footer_text:
                # 🔥 첫 장만 출력 설정 확인 - 제목 페이지도 동일하게 적용
                show_footer = True
                if hasattr(self, 'footer_first_page_only') and self.footer_first_page_only.get():
                    # 제목 페이지가 있을 때는 제목 페이지에만 표시, 피드백 페이지에는 표시하지 않음
                    show_footer = True  # 제목 페이지에는 표시
                
                if show_footer:
                    c.setFont(korean_font, 11)
                    footer_width = c.stringWidth(footer_text, korean_font, 11)
                    c.drawString((width - footer_width) / 2, 40, footer_text)
                
        except Exception as e:
            logger.error(f"제목 페이지 생성 오류: {e}")
            c.setFont('Helvetica', 20)
            c.drawString(100, height - 100, "High Quality Feedback Report")

    def wrap_text_for_pdf(self, text, max_width, font_name, font_size, canvas):
        """PDF용 텍스트 줄바꿈"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if canvas.stringWidth(test_line, font_name, font_size) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines

    def on_mousewheel(self, event):
        """마우스 휠 스크롤"""
        try:
            if self.main_canvas.winfo_exists():
                delta = 1 if event.delta < 0 else -1
                self.main_canvas.yview_scroll(delta, 'units')
        except Exception as e:
            logger.debug(f"마우스 휠 오류: {e}")

    def on_closing(self):
        """프로그램 종료 처리"""
        try:
            if self.feedback_items:
                result = messagebox.askyesnocancel(
                    "종료 확인", 
                    "저장하지 않은 피드백이 있습니다.\n저장하고 종료하시겠습니까?"
                )
                
                if result is None:
                    return
                elif result:
                    self.save_project()
            
            self.cleanup_resources()
            
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            logger.error(f"종료 처리 오류: {e}")
            try:
                self.root.destroy()
            except:
                pass

    def cleanup_resources(self):
        """리소스 정리"""
        try:
            logger.info("리소스 정리 시작...")
            
            if hasattr(self, 'task_manager'):
                self.task_manager.shutdown()
            
            if hasattr(self, 'thread_executor'):
                self.thread_executor.shutdown()
            
            self.undo_manager.clear_all()
            self.clear_selection()
            
            gc.collect()
            
            final_memory = self.system_monitor.get_memory_usage()
            logger.info(f"리소스 정리 완료 - 최종 메모리: {final_memory:.1f}MB")
            
        except Exception as e:
            logger.debug(f"리소스 정리 오류: {e}")

    def save_project(self):
        """프로젝트 저장"""
        try:
            if not self.feedback_items:
                messagebox.showwarning('저장', '저장할 피드백이 없습니다.')
                return
            
            file_path = filedialog.asksaveasfilename(
                defaultextension='.json',
                filetypes=[('JSON 파일', '*.json'), ('모든 파일', '*.*')],
                initialfile=f"{self.project_title.get()}_피드백.json"
            )
            
            if file_path:
                self.save_project_to_file(file_path)
                
        except Exception as e:
            logger.error(f"프로젝트 저장 오류: {e}")
            messagebox.showerror('저장 오류', f'저장 중 오류가 발생했습니다: {str(e)}')

    def save_settings(self):
        """설정 저장"""
        try:
            settings = {
                'pdf_quality': self.pdf_quality.get(),
                'canvas_width': self.canvas_width.get(),
                'canvas_height': self.canvas_height.get(),
                'show_index_numbers': self.show_index_numbers.get(),
                'show_name': self.show_name.get(),
                'show_timestamp': self.show_timestamp.get(),
                'auto_save_interval': self.auto_save_interval.get(),
                'pen_smoothing_strength': self.pen_smoothing_strength.get(),
                'pen_smoothing_enabled': self.pen_smoothing_enabled.get(),  # 🔥 손떨림 방지 설정 저장
                'footer_first_page_only': self.footer_first_page_only.get()
            }
            
            settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
                
            logger.info("설정 저장 완료")
            
        except Exception as e:
            logger.error(f"설정 저장 오류: {e}")
    
    def load_settings(self):
        """설정 불러오기"""
        try:
            settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                self.pdf_quality.set(settings.get('pdf_quality', 300))
                self.canvas_width.set(settings.get('canvas_width', 1000))
                self.canvas_height.set(settings.get('canvas_height', 800))
                self.show_index_numbers.set(settings.get('show_index_numbers', True))
                self.show_name.set(settings.get('show_name', True))
                self.show_timestamp.set(settings.get('show_timestamp', True))
                self.auto_save_interval.set(settings.get('auto_save_interval', 5))
                self.pen_smoothing_strength.set(settings.get('pen_smoothing_strength', 3))
                self.pen_smoothing_enabled.set(settings.get('pen_smoothing_enabled', False))  # 🔥 손떨림 방지 기본값 False
                self.footer_first_page_only.set(settings.get('footer_first_page_only', False))
                
                logger.info("설정 불러오기 완료")
                
        except Exception as e:
            logger.error(f"설정 불러오기 오류: {e}")
            # 오류 시 기본값 사용

    def clear_selection(self):
        """선택 해제"""
        self.selected_annotations = []
        self.selection_rect = None
        self.selection_start = None
        self.drag_start = None
        
        # 드래그 상태 초기화
        self.dragging_text = None
        self.dragging_image = None
        self.drag_start_x = None
        self.drag_start_y = None
        self.original_text_x = None
        self.original_text_y = None
        self.original_image_x = None
        self.original_image_y = None
        
        # 모든 캔버스에서 하이라이트 및 선택 사각형 제거
        try:
            # 활성 캔버스들에서 제거
            if hasattr(self, 'active_canvases'):
                for canvas in self.active_canvases:
                    if canvas.winfo_exists():
                        canvas.delete('highlight')
                        canvas.delete('selection_rect')
            
            # 현재 피드백 카드의 모든 캔버스에서 제거
            if hasattr(self, 'scrollable_frame') and self.scrollable_frame.winfo_exists():
                for widget in self.scrollable_frame.winfo_children():
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Frame):
                            for grandchild in child.winfo_children():
                                if isinstance(grandchild, tk.Canvas):
                                    try:
                                        grandchild.delete('highlight')
                                        grandchild.delete('selection_rect')
                                    except:
                                        pass
        except Exception as e:
            logger.debug(f"선택 해제 오류: {e}")
            pass
    def update_card_borders(self):
        """모든 카드의 테두리 색상 업데이트 - 현재 활성 카드만 파란색"""
        try:
            if not hasattr(self, 'scrollable_frame') or not self.scrollable_frame.winfo_exists():
                return
                
            # 모든 피드백 카드를 순회하며 테두리 색상 업데이트
            for widget in self.scrollable_frame.winfo_children():
                if isinstance(widget, tk.LabelFrame) and hasattr(widget, 'item_index'):
                    # 현재 선택된 카드인지 확인
                    is_current = (widget.item_index == self.current_index)
                    
                    # 테두리 색상 설정
                    if is_current:
                        # 선택된 카드 - 파란색 테두리
                        widget.configure(
                            highlightbackground='#2196F3',
                            highlightcolor='#2196F3',
                            highlightthickness=2
                        )
                    else:
                        # 선택되지 않은 카드 - 회색 테두리
                        widget.configure(
                            highlightbackground='#dee2e6',
                            highlightcolor='#dee2e6',
                            highlightthickness=1
                        )
                    
                    # 카드 내부의 캔버스와 텍스트 영역도 업데이트
                    self.update_card_children_borders(widget, is_current)
                        
            logger.debug(f"카드 테두리 업데이트 완료 - 현재 선택: {self.current_index}")
                        
        except Exception as e:
            logger.debug(f"카드 테두리 업데이트 오류: {e}")

    def update_card_children_borders(self, card_widget, is_current):
        """카드 내부 위젯들의 테두리 업데이트 - 깊은 탐색 지원"""
        try:
            border_color = '#2196F3' if is_current else '#dee2e6'
            thickness = 2 if is_current else 1
            
            def find_and_update_widgets(widget, depth=0):
                """위젯을 재귀적으로 탐색하여 캔버스와 텍스트 위젯 업데이트"""
                if depth > 10:  # 무한 루프 방지
                    return
                    
                try:
                    for child in widget.winfo_children():
                        # 캔버스 발견 시 테두리 업데이트 - 선택 시 두꺼운 파란 테두리
                        if isinstance(child, tk.Canvas):
                            try:
                                if is_current:
                                    # 선택된 카드의 캔버스 - 피드백 입력창과 같은 색상의 2px 테두리
                                    canvas_border_color = '#888888'  # 피드백 입력창과 같은 진한 회색
                                    canvas_thickness = 2  # 2px 테두리
                                else:
                                    # 선택되지 않은 카드의 캔버스 - 얇은 회색 테두리
                                    canvas_border_color = '#888888'  # 진한 회색
                                    canvas_thickness = 1  # 얇은 테두리
                                    
                                child.configure(
                                    highlightbackground=canvas_border_color,
                                    highlightcolor=canvas_border_color,
                                    highlightthickness=canvas_thickness
                                )
                                
                                status = "2px 진한 회색 테두리" if is_current else "1px 회색 테두리"
                                print(f"[캔버스 테두리] 카드 {getattr(card_widget, 'item_index', '?')}: {status}")
                            except Exception as e:
                                print(f"[캔버스 테두리 오류] {e}")
                                
                        # 텍스트 위젯 발견 시 테두리 업데이트 (항상 회색)
                        elif isinstance(child, tk.Text):
                            try:
                                child.configure(
                                    highlightbackground='#dee2e6',
                                    highlightcolor='#dee2e6', 
                                    highlightthickness=1
                                )
                            except:
                                pass
                                
                        # LabelFrame (텍스트 영역) - 항상 회색 유지
                        elif isinstance(child, tk.LabelFrame):
                            try:
                                child.configure(
                                    highlightbackground='#dee2e6',
                                    highlightcolor='#dee2e6',
                                    highlightthickness=1
                                )
                            except:
                                pass
                                
                        # 컨테이너 위젯인 경우 재귀 탐색
                        elif isinstance(child, (tk.Frame, tk.LabelFrame)):
                            find_and_update_widgets(child, depth + 1)
                            
                except Exception as e:
                    print(f"[위젯 탐색 오류] depth {depth}: {e}")
            
            # 카드 내부의 모든 위젯을 재귀적으로 탐색
            find_and_update_widgets(card_widget)
                        
        except Exception as e:
            logger.debug(f"카드 내부 위젯 테두리 업데이트 오류: {e}")

    def bind_canvas_events(self, canvas, item, index, canvas_width, canvas_height):
        """캔버스 이벤트 바인딩 - 완전 수정된 버전"""
        
        # 디버깅을 위한 상태 정보
        drawing_state = {
            'is_drawing': False,
            'start_x': 0,
            'start_y': 0,
            'current_path': [],
            'temp_objects': [],
            'debug_mode': '--debug' in sys.argv or os.getenv('DEBUG_MODE') == '1',  # 동적 디버그 모드
            'last_tool': None
        }
        
        def debug_log(message):
            """디버그 로깅"""
            if drawing_state['debug_mode']:
                logger.debug(f"DEBUG [{index}]: {message}")
        
        def clear_temp_objects():
            """임시 객체 정리"""
            try:
                for obj_id in drawing_state['temp_objects']:
                    if canvas.winfo_exists():
                        canvas.delete(obj_id)
                drawing_state['temp_objects'].clear()
                debug_log("임시 객체 정리 완료")
            except Exception as e:
                debug_log(f"임시 객체 정리 오류: {e}")
                drawing_state['temp_objects'].clear()

        def smooth_pen_path(path_points):
            """향상된 펜 경로 손떨림 방지 처리"""
            if not self.pen_smoothing_enabled.get() or len(path_points) < 3:
                debug_log(f"🎯 스무딩 비활성화 또는 점 부족 - 활성화: {self.pen_smoothing_enabled.get()}, 점 개수: {len(path_points)}")
                return path_points
            
            strength = self.pen_smoothing_strength.get()
            debug_log(f"🎯 최종 스무딩 처리 시작 - 강도: {strength}, 점 개수: {len(path_points)}")
            smoothed = [path_points[0]]
            
            # 다단계 스무딩 적용
            current_points = path_points[:]
            
            # 1단계: 기본 가중 평균 스무딩 (1-10 범위 최적화)
            for iteration in range(min(2, strength // 3 + 1)):  # 반복 횟수 조정
                temp_smoothed = [current_points[0]]
                
                for i in range(1, len(current_points) - 1):
                    # 1-10 범위에 맞춘 가중치 계산
                    base_weight = min(strength / 12.0, 0.8)  # 10에서 최대 80%
                    
                    prev_point = current_points[i - 1]
                    curr_point = current_points[i]
                    next_point = current_points[i + 1]
                    
                    # 거리 기반 가중치 조정
                    dist_prev = ((curr_point[0] - prev_point[0])**2 + (curr_point[1] - prev_point[1])**2)**0.5
                    dist_next = ((next_point[0] - curr_point[0])**2 + (next_point[1] - curr_point[1])**2)**0.5
                    
                    # 강도에 따른 적응형 가중치
                    if strength >= 8:  # 매우 부드러움 (8-10)
                        adaptive_weight = base_weight * (1.0 + 2.0 / max(dist_prev + dist_next, 0.5))
                        adaptive_weight = min(adaptive_weight, 0.8)
                    elif strength >= 5:  # 적당한 부드러움 (5-7)
                        adaptive_weight = base_weight * (1.0 + 1.5 / max(dist_prev + dist_next, 1.0))
                        adaptive_weight = min(adaptive_weight, 0.6)
                    else:  # 가벼운 보정 (1-4)
                        adaptive_weight = base_weight * (1.0 + 1.0 / max(dist_prev + dist_next, 1.5))
                        adaptive_weight = min(adaptive_weight, 0.4)
                    
                    smooth_x = (prev_point[0] * adaptive_weight + curr_point[0] * (1 - 2*adaptive_weight) + next_point[0] * adaptive_weight)
                    smooth_y = (prev_point[1] * adaptive_weight + curr_point[1] * (1 - 2*adaptive_weight) + next_point[1] * adaptive_weight)
                    
                    temp_smoothed.append((smooth_x, smooth_y))
                
                if len(current_points) > 1:
                    temp_smoothed.append(current_points[-1])
                current_points = temp_smoothed
            
            # 2단계: 베지어 곡선 기반 추가 스무딩 (고강도에서 적용)
            if strength >= 6:
                bezier_smoothed = [current_points[0]]
                
                for i in range(1, len(current_points) - 2):
                    p0 = current_points[i-1] if i > 0 else current_points[i]
                    p1 = current_points[i]
                    p2 = current_points[i+1]
                    p3 = current_points[i+2] if i+2 < len(current_points) else current_points[i+1]
                    
                    # 베지어 곡선 제어점 계산
                    t = 0.5  # 중점
                    bezier_x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
                    bezier_y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
                    
                    # 1-10 범위에 맞춘 혼합 비율
                    if strength >= 9:  # 극도로 부드러움 (9-10)
                        mix_ratio = min((strength - 6) / 4.0, 0.5)  # 최대 50%
                    elif strength >= 7:  # 매우 부드러움 (7-8)
                        mix_ratio = min((strength - 6) / 4.0, 0.35)  # 최대 35%
                    else:  # 적당한 부드러움 (6)
                        mix_ratio = min((strength - 6) / 4.0, 0.2)  # 최대 20%
                    
                    final_x = p1[0] * (1 - mix_ratio) + bezier_x * mix_ratio
                    final_y = p1[1] * (1 - mix_ratio) + bezier_y * mix_ratio
                    
                    bezier_smoothed.append((final_x, final_y))
                
                if len(current_points) > 1:
                    bezier_smoothed.append(current_points[-1])
                current_points = bezier_smoothed
            
            # 3단계: 최고강도 전용 추가 스무딩 (9-10)
            if strength >= 9:
                ultra_smoothed = [current_points[0]]
                
                # 다점 가중 평균으로 궁극의 부드러움 구현
                for i in range(1, len(current_points) - 1):
                    # 주변 점들 수집 (강도에 따라 범위 조정)
                    radius = 2 if strength == 10 else 1
                    points_range = []
                    for j in range(max(0, i-radius), min(len(current_points), i+radius+1)):
                        points_range.append(current_points[j])
                    
                    if len(points_range) >= 3:
                        # 가우시안 가중치 적용
                        if len(points_range) == 5:  # 5점
                            weights = [0.1, 0.2, 0.4, 0.2, 0.1]
                        elif len(points_range) == 3:  # 3점
                            weights = [0.25, 0.5, 0.25]
                        else:  # 기타
                            center_idx = len(points_range) // 2
                            weights = [0.1] * len(points_range)
                            weights[center_idx] = 0.5
                            for j in range(len(weights)):
                                if j != center_idx:
                                    weights[j] = 0.5 / (len(weights) - 1)
                        
                        ultra_x = sum(p[0] * w for p, w in zip(points_range, weights))
                        ultra_y = sum(p[1] * w for p, w in zip(points_range, weights))
                        
                        ultra_smoothed.append((ultra_x, ultra_y))
                    else:
                        ultra_smoothed.append(current_points[i])
                
                # 마지막 점 추가
                if len(current_points) > 1:
                    ultra_smoothed.append(current_points[-1])
                current_points = ultra_smoothed
            
            debug_log(f"🎯 스무딩 처리 완료 - 최종 점 개수: {len(current_points)}")
            return current_points

        def get_annotations_in_selection(x1, y1, x2, y2):
            """선택 영역 안의 주석들 찾기"""
            try:
                selected_indices = []
                
                # 영역 정규화
                min_x, max_x = min(x1, x2), max(x1, x2)
                min_y, max_y = min(y1, y2), max(y1, y2)
                
                # 실제 이미지 좌표로 변환
                scale_x = item['image'].width / canvas_width
                scale_y = item['image'].height / canvas_height
                
                real_min_x = min_x * scale_x
                real_max_x = max_x * scale_x
                real_min_y = min_y * scale_y
                real_max_y = max_y * scale_y
                
                for i, annotation in enumerate(item.get('annotations', [])):
                    if self.annotation_in_rect(annotation, real_min_x, real_min_y, real_max_x, real_max_y):
                        selected_indices.append(i)
                
                return selected_indices
                
            except Exception as e:
                debug_log(f"주석 선택 영역 검사 오류: {e}")
                return []

        def unified_mouse_handler(event):
            """통합 마우스 이벤트 처리기"""
            debug_log(f"🖱️ 통합 마우스 이벤트: {event.type}, 도구: {self.current_tool}, x={event.x}, y={event.y}")
            
            # 현재 항목으로 설정 (항상)
            if self.current_index != index:
                debug_log(f"현재 항목 변경: {self.current_index} -> {index}")
                self.current_index = index
                self.update_card_borders()  # 카드 테두리 업데이트
                self.update_status()
            
            # 포커스 설정
            canvas.focus_set()
            
            # 이벤트 타입별 처리
            if event.type == '4':  # ButtonPress
                handle_button_press(event)
            elif event.type == '6':  # Motion
                handle_button_motion(event)
            elif event.type == '5':  # ButtonRelease
                handle_button_release(event)

        def handle_button_press(event):
            """마우스 버튼 누름 처리"""
            debug_log(f"🖱️ 마우스 누름 - 도구: {self.current_tool}")
            
            # 선택 도구가 아닌 경우에만 그리기 시작
            if self.current_tool != 'select':
                # 기존 선택 해제 및 임시 객체 정리
                self.clear_selection()
                clear_temp_objects()
                
                # 그리기 상태 초기화
                drawing_state['is_drawing'] = True
                drawing_state['start_x'] = event.x
                drawing_state['start_y'] = event.y
                drawing_state['current_path'] = [(event.x, event.y)]
                drawing_state['last_tool'] = self.current_tool
                
                debug_log(f"그리기 시작 - 도구: {self.current_tool}, 시작점: ({event.x}, {event.y})")
                
                # 텍스트 도구는 즉시 처리
                if self.current_tool == 'text':
                    drawing_state['is_drawing'] = False
                    debug_log("텍스트 도구 - 입력창 표시")
                    handle_text_annotation_immediate(event)
                return
            else:
                # 선택 도구 처리 - 주석 드래그 체크 (텍스트, 이미지 포함)
                for annotation in item['annotations']:
                    if annotation['type'] == 'text':
                        text_x = annotation['x'] * (canvas_width / item['image'].width)
                        text_y = annotation['y'] * (canvas_height / item['image'].height)
                        text = annotation.get('text', '')
                        # 원본 폰트 크기 유지 (드래그 감지용)
                        font_size = annotation.get('font_size', 14)
                        
                        # 텍스트 영역 계산 (anchor='nw' 기준으로 수정)
                        text_width = max(len(text) * font_size * 0.7, 60)  # 최소 60px 보장, 더 넓게
                        text_height = max(font_size * 1.5, 25)  # 최소 25px 보장, 더 높게
                        
                        # 클릭 영역을 더 크게 하기 위한 마진 추가
                        margin = 15  # 상하좌우 15px 여유 마진
                        # nw 앵커이므로 text_x, text_y가 왼쪽 상단 모서리
                        click_x1 = text_x - margin
                        click_y1 = text_y - margin
                        click_x2 = text_x + text_width + margin
                        click_y2 = text_y + text_height + margin
                        
                        # 마우스가 확장된 텍스트 영역 안에 있는지 확인
                        if (click_x1 <= event.x <= click_x2 and
                            click_y1 <= event.y <= click_y2):
                            self.dragging_text = annotation
                            self.drag_start_x = event.x
                            self.drag_start_y = event.y
                            self.original_text_x = annotation['x']
                            self.original_text_y = annotation['y']
                            debug_log(f"텍스트 주석 드래그 시작: '{text}' (확장된 클릭 영역)")
                            return
                    
                    elif annotation['type'] == 'image':
                        # 이미지 주석 드래그 체크
                        image_x = annotation['x'] * (canvas_width / item['image'].width)
                        image_y = annotation['y'] * (canvas_height / item['image'].height)
                        image_width = annotation['width'] * (canvas_width / item['image'].width)
                        image_height = annotation['height'] * (canvas_height / item['image'].height)
                        
                        # 클릭 영역을 약간 확장
                        margin = 5
                        click_x1 = image_x - margin
                        click_y1 = image_y - margin
                        click_x2 = image_x + image_width + margin
                        click_y2 = image_y + image_height + margin
                        
                        # 마우스가 이미지 영역 안에 있는지 확인
                        if (click_x1 <= event.x <= click_x2 and
                            click_y1 <= event.y <= click_y2):
                            self.dragging_image = annotation
                            self.drag_start_x = event.x
                            self.drag_start_y = event.y
                            self.original_image_x = annotation['x']
                            self.original_image_y = annotation['y']
                            debug_log(f"🖼️ 이미지 주석 드래그 시작 - 위치: ({annotation['x']}, {annotation['y']})")
                            print(f"🖼️ 이미지 주석 드래그 시작 - 위치: ({annotation['x']}, {annotation['y']})")  # 콘솔 출력
                            return
                
                # 텍스트 드래그가 아닌 경우 영역 선택 모드
                self.clear_selection()
                self.selection_start = (event.x, event.y)
                drawing_state['is_drawing'] = True
                drawing_state['start_x'] = event.x
                drawing_state['start_y'] = event.y
                debug_log("선택 도구 - 영역 선택 시작")

        def handle_button_motion(event):
            """마우스 이동 처리"""
            try:
                # 텍스트 주석 드래그 처리
                if self.dragging_text:
                    # 이동 거리 계산 (캔버스 좌표계)
                    dx = event.x - self.drag_start_x
                    dy = event.y - self.drag_start_y
                    
                    # 이미지 좌표계로 변환
                    scale_x = item['image'].width / canvas_width
                    scale_y = item['image'].height / canvas_height
                    
                    # 새 위치 계산 (이미지 좌표계)
                    self.dragging_text['x'] = self.original_text_x + (dx * scale_x)
                    self.dragging_text['y'] = self.original_text_y + (dy * scale_y)
                    
                    # 화면 갱신
                    canvas.delete('annotation')
                    self.draw_annotations(canvas, item, canvas_width, canvas_height)
                    debug_log(f"텍스트 드래그 중: dx={dx}, dy={dy}")
                    return
                
                # 이미지 주석 드래그 처리
                if hasattr(self, 'dragging_image') and self.dragging_image:
                    # 이동 거리 계산 (캔버스 좌표계)
                    dx = event.x - self.drag_start_x
                    dy = event.y - self.drag_start_y
                    
                    # 이미지 좌표계로 변환
                    scale_x = item['image'].width / canvas_width
                    scale_y = item['image'].height / canvas_height
                    
                    # 새 위치 계산 (이미지 좌표계)
                    self.dragging_image['x'] = self.original_image_x + (dx * scale_x)
                    self.dragging_image['y'] = self.original_image_y + (dy * scale_y)
                    
                    # 화면 갱신
                    canvas.delete('annotation')
                    self.draw_annotations(canvas, item, canvas_width, canvas_height)
                    debug_log(f"🖼️ 이미지 드래그 중: dx={dx}, dy={dy}, 새 위치: ({self.dragging_image['x']:.1f}, {self.dragging_image['y']:.1f})")
                    print(f"🖼️ 이미지 드래그 중: dx={dx}, dy={dy}, 새 위치: ({self.dragging_image['x']:.1f}, {self.dragging_image['y']:.1f})")  # 콘솔 출력
                    return
            
                if not drawing_state['is_drawing']:
                    return
                
                if self.current_tool == 'select':
                    # 영역 선택 사각형 그리기
                    canvas.delete('selection_rect')
                    start_x = drawing_state['start_x']
                    start_y = drawing_state['start_y']
                    
                    self.selection_rect = canvas.create_rectangle(
                        start_x, start_y, event.x, event.y,
                        outline='blue', width=2, dash=(5, 5), tags='selection_rect'
                    )
                    return
                
                elif self.current_tool == 'pen':
                    # 펜 도구 - 향상된 연속 선 그리기
                    new_point = (event.x, event.y)
                    
                    # 점 간격 최적화: 너무 가까운 점들 필터링
                    min_distance = max(1, self.line_width // 2)  # 선 두께에 따른 동적 최소 거리
                    should_add_point = True
                    
                    if len(drawing_state['current_path']) > 0:
                        last_point = drawing_state['current_path'][-1]
                        distance = ((new_point[0] - last_point[0])**2 + (new_point[1] - last_point[1])**2)**0.5
                        
                        # 거리가 너무 가까우면 점 추가하지 않음
                        if distance < min_distance:
                            should_add_point = False
                    
                    if should_add_point:
                        drawing_state['current_path'].append(new_point)
                    
                    if len(drawing_state['current_path']) >= 2:
                        clear_temp_objects()
                        
                        # 실시간 스무딩 적용된 경로 그리기
                        current_path = drawing_state['current_path']
                        
                        # 향상된 실시간 스무딩
                        if self.pen_smoothing_enabled.get() and len(current_path) >= 3:
                            display_path = []
                            display_path.append(current_path[0])  # 첫 점은 그대로
                            
                            strength = self.pen_smoothing_strength.get()
                            debug_log(f"🎨 실시간 스무딩 적용 - 강도: {strength}")
                            
                            # 1-10 범위에 맞춘 실시간 스무딩 팩터 결정
                            if strength >= 9:
                                # 극도로 부드러움 (9-10)
                                smooth_factor = 0.4
                                debug_log(f"🎨 극도로 부드러움 모드 (팩터: {smooth_factor})")
                            elif strength >= 7:
                                # 매우 부드러움 (7-8)
                                smooth_factor = 0.3
                                debug_log(f"🎨 매우 부드러움 모드 (팩터: {smooth_factor})")
                            elif strength >= 5:
                                # 적당한 부드러움 (5-6)
                                smooth_factor = 0.2
                                debug_log(f"🎨 적당한 부드러움 모드 (팩터: {smooth_factor})")
                            else:
                                # 가벼운 보정 (1-4)
                                smooth_factor = 0.1
                                debug_log(f"🎨 가벼운 보정 모드 (팩터: {smooth_factor})")
                            
                            # 중간 점들에 스무딩 적용
                            for i in range(1, len(current_path) - 1):
                                p_prev = current_path[i-1]
                                p_curr = current_path[i]
                                p_next = current_path[i+1]
                                
                                smooth_x = p_curr[0] * (1 - smooth_factor) + (p_prev[0] + p_next[0]) * smooth_factor / 2
                                smooth_y = p_curr[1] * (1 - smooth_factor) + (p_prev[1] + p_next[1]) * smooth_factor / 2
                                
                                display_path.append((smooth_x, smooth_y))
                            
                            display_path.append(current_path[-1])  # 마지막 점은 그대로
                        else:
                            display_path = current_path
                        
                        # 실시간 미리보기 선 그리기 (빨간색 가이드 선)
                        if len(display_path) > 1:
                            # 연결된 선으로 그리기 (더 부드럽게)
                            points = []
                            for x, y in display_path:
                                points.extend([x, y])
                            
                            obj_id = canvas.create_line(
                                points,
                                fill='red',  # 빨간색 가이드 선
                                width=max(1, self.line_width - 1),  # 약간 더 얇게
                                capstyle='round', joinstyle='round',
                                smooth=True,
                                tags='drawing_temp'
                            )
                            drawing_state['temp_objects'].append(obj_id)
                        
                        canvas.tag_raise('drawing_temp', 'background')
                
                elif self.current_tool in ['arrow', 'line', 'oval', 'rect']:
                    # 도형 도구 - 미리보기
                    clear_temp_objects()
                    
                    start_x = drawing_state['start_x']
                    start_y = drawing_state['start_y']
                    end_x = event.x
                    end_y = event.y
                    
                    if self.current_tool == 'arrow':
                        # 화살표 미리보기
                        line_id = canvas.create_line(
                            start_x, start_y, end_x, end_y, 
                            fill=self.annotation_color, 
                            width=self.line_width, 
                            tags='drawing_temp'
                        )
                        drawing_state['temp_objects'].append(line_id)
                        
                        # 🔥 개선된 화살표 머리 그리기 (임시 미리보기용)
                        if abs(end_x - start_x) > 5 or abs(end_y - start_y) > 5:
                            import math
                            # 화살표 길이와 선 두께에 따라 동적 크기 계산
                            arrow_length = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
                            base_arrow_size = max(8, self.line_width * 2.5)
                            max_arrow_size = arrow_length * 0.3
                            arrow_size = min(base_arrow_size, max_arrow_size)
                            arrow_size = max(arrow_size, 6)
                            
                            angle = math.atan2(end_y - start_y, end_x - start_x)
                            angle_offset = math.pi / 8 if arrow_size < 12 else math.pi / 6
                            
                            # 🔥 돌출된 삼각형 끝점 계산
                            extend_distance = arrow_size * 0.15
                            tip_x = end_x + extend_distance * math.cos(angle)
                            tip_y = end_y + extend_distance * math.sin(angle)
                            
                            # 화살표 머리 좌표 계산 (원래 끝점 기준)
                            wing1_x = end_x - arrow_size * math.cos(angle - angle_offset)
                            wing1_y = end_y - arrow_size * math.sin(angle - angle_offset)
                            wing2_x = end_x - arrow_size * math.cos(angle + angle_offset)
                            wing2_y = end_y - arrow_size * math.sin(angle + angle_offset)
                            
                            # 🔥 뾰족하고 돌출된 삼각형 임시 미리보기
                            temp_arrow_head = canvas.create_polygon(
                                tip_x, tip_y,      # 더 앞으로 돌출된 끝점
                                wing1_x, wing1_y,  # 왼쪽 날개
                                wing2_x, wing2_y,  # 오른쪽 날개
                                fill=self.annotation_color,
                                outline=self.annotation_color,
                                tags='drawing_temp'
                            )
                            drawing_state['temp_objects'].append(temp_arrow_head)
                    
                    elif self.current_tool == 'line':
                        # 라인 미리보기 (화살표 머리 없는 단순한 선)
                        line_id = canvas.create_line(
                            start_x, start_y, end_x, end_y, 
                            fill=self.annotation_color, 
                            width=self.line_width, 
                            tags='drawing_temp'
                        )
                        drawing_state['temp_objects'].append(line_id)
                    
                    elif self.current_tool == 'oval':
                        oval_id = canvas.create_oval(
                            start_x, start_y, end_x, end_y,
                            outline=self.annotation_color, 
                            width=self.line_width,
                            tags='drawing_temp'
                        )
                        drawing_state['temp_objects'].append(oval_id)
                    
                    elif self.current_tool == 'rect':
                        rect_id = canvas.create_rectangle(
                            start_x, start_y, end_x, end_y,
                            outline=self.annotation_color, 
                            width=self.line_width,
                            tags='drawing_temp'
                        )
                        drawing_state['temp_objects'].append(rect_id)
                    
                    canvas.tag_raise('drawing_temp', 'background')
            
            except Exception as e:
                debug_log(f"마우스 이동 오류: {e}")

        def handle_button_release(event):
            """마우스 버튼 놓음 처리 - 주석 실제 추가"""
            debug_log(f"🖱️ 마우스 놓음 - 도구: {self.current_tool}, 그리기 중: {drawing_state['is_drawing']}")
            
            # 텍스트 주석 드래그 종료
            if self.dragging_text:
                # 상태 저장 (실제 이동이 있었을 경우에만)
                if (self.dragging_text['x'] != self.original_text_x or 
                    self.dragging_text['y'] != self.original_text_y):
                    self.undo_manager.save_state(item['id'], item['annotations'])
                    debug_log("텍스트 주석 이동 완료 - 상태 저장됨")
                    self.update_status_message("📝 텍스트 주석이 이동되었습니다", 2000)
                
                self.dragging_text = None
                self.drag_start_x = None
                self.drag_start_y = None
                self.original_text_x = None
                self.original_text_y = None
                return
            
            # 이미지 주석 드래그 종료
            if hasattr(self, 'dragging_image') and self.dragging_image:
                # 상태 저장 (실제 이동이 있었을 경우에만)
                if (self.dragging_image['x'] != self.original_image_x or 
                    self.dragging_image['y'] != self.original_image_y):
                    self.undo_manager.save_state(item['id'], item['annotations'])
                    debug_log("🖼️ 이미지 주석 이동 완료 - 상태 저장됨")
                    print(f"🖼️ 이미지 주석 이동 완료 - 최종 위치: ({self.dragging_image['x']:.1f}, {self.dragging_image['y']:.1f})")  # 콘솔 출력
                    self.update_status_message("🖼️ 이미지 주석이 이동되었습니다", 2000)
                
                self.dragging_image = None
                self.drag_start_x = None
                self.drag_start_y = None
                self.original_image_x = None
                self.original_image_y = None
                return
            
            if not drawing_state['is_drawing']:
                debug_log("그리기 상태가 아님 - 종료")
                return
            
            try:
                drawing_state['is_drawing'] = False
                
                if self.current_tool == 'select':
                    # 영역 선택 완료
                    start_x = drawing_state['start_x']
                    start_y = drawing_state['start_y']
                    end_x = event.x
                    end_y = event.y
                    
                    # 선택 영역이 충분히 큰 경우에만 처리
                    if abs(end_x - start_x) > 10 and abs(end_y - start_y) > 10:
                        selected_indices = get_annotations_in_selection(start_x, start_y, end_x, end_y)
                        
                        if selected_indices:
                            # 선택된 주석들 저장
                            self.selected_annotations = [item['annotations'][i] for i in selected_indices]
                            # 선택된 주석들 하이라이트
                            self.highlight_selected_annotations(canvas, canvas_width, canvas_height)
                            self.update_status_message(f"{len(selected_indices)}개 주석이 선택되었습니다")
                            debug_log(f"주석 선택 완료: {len(selected_indices)}개")
                        else:
                            self.update_status_message("선택 영역에 주석이 없습니다")
                            debug_log("선택 영역에 주석 없음")
                    
                    # 선택 사각형 제거
                    canvas.delete('selection_rect')
                    self.selection_rect = None
                    return
                
                # 주석 추가 로직
                debug_log("실행 취소용 상태 저장 중...")
                self.undo_manager.save_state(item['id'], item['annotations'])
                
                # 주석 추가
                annotation_added = False
                
                if self.current_tool == 'pen' and len(drawing_state['current_path']) > 1:
                    debug_log(f"펜 주석 추가 시작 - 점 개수: {len(drawing_state['current_path'])}")
                    annotation_added = add_pen_annotation_direct(
                        drawing_state['current_path'], item, canvas_width, canvas_height
                    )
                    
                elif self.current_tool == 'arrow':
                    debug_log("화살표 주석 추가 시작")
                    annotation_added = add_arrow_annotation_direct(
                        drawing_state['start_x'], drawing_state['start_y'],
                        event.x, event.y, item, canvas_width, canvas_height
                    )
                    
                elif self.current_tool == 'line':
                    debug_log("라인 주석 추가 시작")
                    annotation_added = add_line_annotation_direct(
                        drawing_state['start_x'], drawing_state['start_y'],
                        event.x, event.y, item, canvas_width, canvas_height
                    )
                    
                elif self.current_tool in ['oval', 'rect']:
                    debug_log(f"{self.current_tool} 주석 추가 시작")
                    annotation_added = add_shape_annotation_direct(
                        self.current_tool, drawing_state['start_x'], drawing_state['start_y'],
                        event.x, event.y, item, canvas_width, canvas_height
                    )
                
                # 임시 객체 정리
                clear_temp_objects()
                
                if annotation_added:
                    debug_log("✅ 주석 추가 성공 - 화면 새로고침")
                    # 주석 다시 그리기
                    canvas.delete('annotation')
                    self.draw_annotations(canvas, item, canvas_width, canvas_height)
                    canvas.tag_lower('background')
                    debug_log(f"총 주석 개수: {len(item.get('annotations', []))}")
                    self.update_status_message("주석이 추가되었습니다")
                else:
                    debug_log("❌ 주석 추가 실패")
                    self.update_status_message("주석 추가 실패")
                
            except Exception as e:
                debug_log(f"마우스 놓음 처리 오류: {e}")
                clear_temp_objects()

        def handle_text_annotation_immediate(event):
            """즉시 텍스트 주석 처리 - 커스텀 폰트/색상 지원"""
            try:
                from tkinter import simpledialog
                
                # 🔥 개선된 커스텀 텍스트 입력 대화상자
                text_input = self.show_custom_text_dialog()
                
                # 새로운 형식 처리: dict 또는 기존 문자열
                if text_input:
                    if isinstance(text_input, dict):
                        # 새로운 형식: 폰트 설정 포함
                        text_content = text_input.get('text', '').strip()
                        font_size = text_input.get('font_size', self.font_size)
                        color = text_input.get('color', self.annotation_color)
                    elif isinstance(text_input, str):
                        # 기존 형식: 문자열만
                        text_content = text_input.strip()
                        font_size = self.font_size
                        color = self.annotation_color
                    else:
                        return
                    
                    if text_content:
                        # 실행 취소를 위한 상태 저장
                        self.undo_manager.save_state(item['id'], item['annotations'])
                        
                        # 이미지 좌표로 변환
                        scale_x = item['image'].width / canvas_width
                        scale_y = item['image'].height / canvas_height
                        
                        # 🔥 주석 데이터 생성 (커스텀 폰트/색상 포함)
                        annotation = {
                            'type': 'text',
                            'x': event.x * scale_x,
                            'y': event.y * scale_y,
                            'text': text_content,
                            'color': color,
                            'font_size': font_size
                        }
                        
                        # 주석 추가
                        item['annotations'].append(annotation)
                        debug_log(f"✅ 텍스트 주석 추가 완료: '{text_content}' (크기:{font_size}, 색상:{color})")
                        
                        # 화면 새로고침
                        canvas.delete('annotation')
                        self.draw_annotations(canvas, item, canvas_width, canvas_height)
                        canvas.tag_lower('background')
                        self.update_status_message(f"텍스트 주석이 추가되었습니다 ({font_size}px)")
                    
            except Exception as e:
                debug_log(f"텍스트 주석 오류: {e}")

        def add_pen_annotation_direct(path_points, item, canvas_width, canvas_height):
            """펜 주석 직접 추가"""
            try:
                if len(path_points) < 2:
                    return False
                
                # 이미지 좌표로 변환
                scale_x = item['image'].width / canvas_width
                scale_y = item['image'].height / canvas_height
                scaled_points = [(x * scale_x, y * scale_y) for x, y in path_points]
                
                # 주석 데이터 생성
                annotation = {
                    'type': 'pen',
                    'points': scaled_points,
                    'color': self.annotation_color,
                    'width': self.line_width
                }
                
                # 주석 추가
                item['annotations'].append(annotation)
                debug_log(f"펜 주석 추가 완료: {len(scaled_points)}개 점")
                return True
                
            except Exception as e:
                debug_log(f"펜 주석 추가 오류: {e}")
                return False

        def add_arrow_annotation_direct(start_x, start_y, end_x, end_y, item, canvas_width, canvas_height):
            """화살표 주석 직접 추가"""
            try:
                # 최소 거리 확인
                if abs(end_x - start_x) < 5 and abs(end_y - start_y) < 5:
                    return False
                
                # 이미지 좌표로 변환
                scale_x = item['image'].width / canvas_width
                scale_y = item['image'].height / canvas_height
                
                # 주석 데이터 생성
                annotation = {
                    'type': 'arrow',
                    'start_x': start_x * scale_x,
                    'start_y': start_y * scale_y,
                    'end_x': end_x * scale_x,
                    'end_y': end_y * scale_y,
                    'color': self.annotation_color,
                    'width': self.line_width
                }
                
                # 주석 추가
                item['annotations'].append(annotation)
                debug_log(f"화살표 주석 추가 완료")
                return True
                
            except Exception as e:
                debug_log(f"화살표 주석 추가 오류: {e}")
                return False

        def add_line_annotation_direct(start_x, start_y, end_x, end_y, item, canvas_width, canvas_height):
            """라인 주석 직접 추가"""
            try:
                # 최소 거리 확인
                if abs(end_x - start_x) < 5 and abs(end_y - start_y) < 5:
                    return False
                
                # 이미지 좌표로 변환
                scale_x = item['image'].width / canvas_width
                scale_y = item['image'].height / canvas_height
                
                # 주석 데이터 생성
                annotation = {
                    'type': 'line',
                    'start_x': start_x * scale_x,
                    'start_y': start_y * scale_y,
                    'end_x': end_x * scale_x,
                    'end_y': end_y * scale_y,
                    'color': self.annotation_color,
                    'width': self.line_width
                }
                
                # 주석 추가
                item['annotations'].append(annotation)
                debug_log(f"라인 주석 추가 완료")
                return True
                
            except Exception as e:
                debug_log(f"라인 주석 추가 오류: {e}")
                return False

        def add_shape_annotation_direct(shape_type, x1, y1, x2, y2, item, canvas_width, canvas_height):
            """도형 주석 직접 추가"""
            try:
                # 최소 크기 확인
                if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
                    return False
                
                # 이미지 좌표로 변환
                scale_x = item['image'].width / canvas_width
                scale_y = item['image'].height / canvas_height
                
                # 주석 데이터 생성
                annotation = {
                    'type': shape_type,
                    'x1': x1 * scale_x,
                    'y1': y1 * scale_y,
                    'x2': x2 * scale_x,
                    'y2': y2 * scale_y,
                    'color': self.annotation_color,
                    'width': self.line_width
                }
                
                # 주석 추가
                item['annotations'].append(annotation)
                debug_log(f"{shape_type} 주석 추가 완료")
                return True
                
            except Exception as e:
                debug_log(f"{shape_type} 주석 추가 오류: {e}")
                return False

        def handle_key_press(event):
            """키보드 이벤트 처리"""
            try:
                if self.selected_annotations:
                    if event.keysym == 'Delete' or event.keysym == 'BackSpace':
                        self.delete_selected_annotations()
                    elif event.keysym == 'Return' or event.keysym == 'space':
                        # Enter 키나 스페이스바로 편집
                        if len(self.selected_annotations) == 1:
                            annotation = self.selected_annotations[0]
                            if annotation['type'] == 'image':
                                self.edit_annotation_image(annotation)
                            elif annotation['type'] == 'text':
                                # 🔥 텍스트 편집 시 폰트/색상/볼드 설정 지원 (기존 값 로드)
                                existing_text = annotation.get('text', '')
                                existing_font_size = annotation.get('font_size', self.font_size)
                                existing_color = annotation.get('color', self.annotation_color)
                                existing_bold = annotation.get('bold', False)
                                
                                text_input = self.show_custom_text_dialog(
                                    initial_text=existing_text,
                                    initial_font_size=existing_font_size,
                                    initial_color=existing_color,
                                    initial_bold=existing_bold
                                )
                                if text_input:
                                    if isinstance(text_input, dict):
                                        # 새로운 형식: 폰트 설정 포함
                                        text_content = text_input.get('text', '').strip()
                                        if text_content:
                                            annotation['text'] = text_content
                                            annotation['font_size'] = text_input.get('font_size', annotation.get('font_size', self.font_size))
                                            annotation['color'] = text_input.get('color', annotation.get('color', self.annotation_color))
                                            annotation['bold'] = text_input.get('bold', annotation.get('bold', False))
                                    elif isinstance(text_input, str):
                                        # 기존 형식: 문자열만
                                        text_content = text_input.strip()
                                        if text_content:
                                            annotation['text'] = text_content
                                    
                                    self.refresh_current_item()
            except Exception as e:
                debug_log(f"키 입력 오류: {e}")

        # 🔥 핵심! 기존 모든 이벤트 바인딩 제거 후 통합 이벤트 핸들러로 바인딩
        try:
            # 기존 이벤트 바인딩 완전 제거
            canvas.unbind_all('<Button-1>')
            canvas.unbind_all('<B1-Motion>')
            canvas.unbind_all('<ButtonRelease-1>')
            canvas.unbind('<Button-1>')
            canvas.unbind('<B1-Motion>')
            canvas.unbind('<ButtonRelease-1>')
            debug_log("기존 이벤트 바인딩 제거 완료")
        except:
            pass
        
        def handle_mouse_motion(event):
            """마우스 움직임 처리 - 도구별 커서 및 텍스트 주석 hover 효과"""
            try:
                # 도구별 기본 커서 설정
                cursor_map = {
                    'select': 'crosshair',      # 선택: 십자 커서
                    'arrow': 'arrow',           # 화살표: 화살표 커서  
                    'pen': 'target',            # 펜: 동그라미 커서
                    'oval': 'crosshair',        # 원형: 십자 커서
                    'rect': 'crosshair',        # 사각형: 십자 커서
                    'text': 'crosshair'         # 텍스트: 십자 커서
                }
                
                default_cursor = cursor_map.get(self.current_tool, 'crosshair')
                
                # 선택 도구일 때만 주석 hover 효과 적용
                if self.current_tool == 'select':
                    # 드래그 가능한 주석 위에 마우스가 있는지 확인
                    over_draggable = False
                    for annotation in item['annotations']:
                        if annotation['type'] == 'text':
                            text_x = annotation['x'] * (canvas_width / item['image'].width)
                            text_y = annotation['y'] * (canvas_height / item['image'].height)
                            text = annotation.get('text', '')
                            font_size = annotation.get('font_size', 14)
                            
                            # 확장된 클릭 영역 계산 (anchor='nw' 기준)
                            text_width = max(len(text) * font_size * 0.7, 60)
                            text_height = max(font_size * 1.5, 25)
                            margin = 15
                            # nw 앵커이므로 text_x, text_y가 왼쪽 상단 모서리
                            click_x1 = text_x - margin
                            click_y1 = text_y - margin
                            click_x2 = text_x + text_width + margin
                            click_y2 = text_y + text_height + margin
                            
                            if (click_x1 <= event.x <= click_x2 and
                                click_y1 <= event.y <= click_y2):
                                over_draggable = True
                                break
                        
                        elif annotation['type'] == 'image':
                            # 이미지 주석 호버 감지
                            image_x = annotation['x'] * (canvas_width / item['image'].width)
                            image_y = annotation['y'] * (canvas_height / item['image'].height)
                            image_width = annotation['width'] * (canvas_width / item['image'].width)
                            image_height = annotation['height'] * (canvas_height / item['image'].height)
                            
                            # 클릭 영역을 약간 확장
                            margin = 5
                            click_x1 = image_x - margin
                            click_y1 = image_y - margin
                            click_x2 = image_x + image_width + margin
                            click_y2 = image_y + image_height + margin
                            
                            if (click_x1 <= event.x <= click_x2 and
                                click_y1 <= event.y <= click_y2):
                                over_draggable = True
                                break
                    
                    # 드래그 가능한 주석 위에 있으면 손가락 커서, 아니면 기본 커서
                    if over_draggable:
                        canvas.configure(cursor='hand2')
                    else:
                        canvas.configure(cursor=default_cursor)
                else:
                    # 다른 도구들은 해당 도구의 커서 사용
                    canvas.configure(cursor=default_cursor)
                        
            except Exception as e:
                pass  # hover 효과는 오류가 나도 계속 동작해야 함

        def handle_double_click(event):
            """더블클릭으로 주석 편집"""
            try:
                if self.current_tool == 'select':
                    # 클릭한 위치의 주석 찾기
                    for annotation in item['annotations']:
                        if annotation['type'] == 'image':
                            # 이미지 주석 더블클릭 체크
                            image_x = annotation['x'] * (canvas_width / item['image'].width)
                            image_y = annotation['y'] * (canvas_height / item['image'].height)
                            image_width = annotation['width'] * (canvas_width / item['image'].width)
                            image_height = annotation['height'] * (canvas_height / item['image'].height)
                            
                            if (image_x <= event.x <= image_x + image_width and
                                image_y <= event.y <= image_y + image_height):
                                self.edit_annotation_image(annotation)
                                return
                        
                        elif annotation['type'] == 'text':
                            # 텍스트 주석 더블클릭 체크
                            text_x = annotation['x'] * (canvas_width / item['image'].width)
                            text_y = annotation['y'] * (canvas_height / item['image'].height)
                            text = annotation.get('text', '')
                            font_size = annotation.get('font_size', 14)
                            
                            text_width = max(len(text) * font_size * 0.7, 60)
                            text_height = max(font_size * 1.5, 25)
                            
                            if (text_x <= event.x <= text_x + text_width and
                                text_y <= event.y <= text_y + text_height):
                                # 🔥 기존 값들을 모두 전달하여 편집
                                existing_text = annotation.get('text', '')
                                existing_font_size = annotation.get('font_size', self.font_size)
                                existing_color = annotation.get('color', self.annotation_color)
                                existing_bold = annotation.get('bold', False)
                                
                                text_input = self.show_custom_text_dialog(
                                    initial_text=existing_text,
                                    initial_font_size=existing_font_size,
                                    initial_color=existing_color,
                                    initial_bold=existing_bold
                                )
                                if text_input:
                                    if isinstance(text_input, dict):
                                        # 새로운 형식: 폰트 설정 포함
                                        text_content = text_input.get('text', '').strip()
                                        if text_content:
                                            annotation['text'] = text_content
                                            annotation['font_size'] = text_input.get('font_size', annotation.get('font_size', self.font_size))
                                            annotation['color'] = text_input.get('color', annotation.get('color', self.annotation_color))
                                            annotation['bold'] = text_input.get('bold', annotation.get('bold', False))
                                    elif isinstance(text_input, str):
                                        # 기존 형식: 문자열만
                                        text_content = text_input.strip()
                                        if text_content:
                                            annotation['text'] = text_content
                                    
                                    self.refresh_current_item()
                                return
            except Exception as e:
                debug_log(f"더블클릭 처리 오류: {e}")

        # 통합 이벤트 핸들러 바인딩 (충돌 방지)
        canvas.bind('<Button-1>', unified_mouse_handler)
        canvas.bind('<B1-Motion>', unified_mouse_handler) 
        canvas.bind('<ButtonRelease-1>', unified_mouse_handler)
        canvas.bind('<Double-Button-1>', handle_double_click)  # 더블클릭 이벤트 추가
        canvas.bind('<Motion>', handle_mouse_motion)  # 마우스 움직임 이벤트 추가
        canvas.bind('<KeyPress>', handle_key_press)
        canvas.configure(takefocus=True)
        
        debug_log(f"통합 이벤트 바인딩 완료 - 캔버스: {canvas}")

    def draw_annotations(self, canvas, item, canvas_width, canvas_height):
        """주석 그리기 - 들여쓰기 완전 수정"""
        if not item.get('annotations'):
            return
        
        try:
            scale_x = canvas_width / item['image'].width
            scale_y = canvas_height / item['image'].height
            
            for annotation in item['annotations']:
                try:
                    ann_type = annotation['type']
                    color = annotation.get('color', '#ff0000')
                    width = max(1, annotation.get('width', 2))
                    
                    if ann_type == 'arrow':
                        x1 = annotation['start_x'] * scale_x
                        y1 = annotation['start_y'] * scale_y
                        x2 = annotation['end_x'] * scale_x
                        y2 = annotation['end_y'] * scale_y
                        
                        canvas.create_line(x1, y1, x2, y2, fill=color, width=width, tags='annotation')
                        
                        if abs(x2 - x1) > 1 or abs(y2 - y1) > 1:
                            angle = math.atan2(y2 - y1, x2 - x1)
                            arrow_length = 15
                            arrow_angle = math.pi / 6
                            
                            arrow_x1 = x2 - arrow_length * math.cos(angle - arrow_angle)
                            arrow_y1 = y2 - arrow_length * math.sin(angle - arrow_angle)
                            arrow_x2 = x2 - arrow_length * math.cos(angle + arrow_angle)
                            arrow_y2 = y2 - arrow_length * math.sin(angle + arrow_angle)
                            
                            canvas.create_line(x2, y2, arrow_x1, arrow_y1, fill=color, width=width, tags='annotation')
                            canvas.create_line(x2, y2, arrow_x2, arrow_y2, fill=color, width=width, tags='annotation')
                    
                    elif ann_type == 'line':
                        # 라인 그리기 (화살표 머리 없는 단순한 선)
                        x1 = annotation['start_x'] * scale_x
                        y1 = annotation['start_y'] * scale_y
                        x2 = annotation['end_x'] * scale_x
                        y2 = annotation['end_y'] * scale_y
                        
                        canvas.create_line(x1, y1, x2, y2, fill=color, width=width, tags='annotation')
                    
                    elif ann_type == 'pen':
                        points = annotation.get('points', [])
                        if len(points) > 1:
                            scaled_points = []
                            for x, y in points:
                                scaled_points.extend([x * scale_x, y * scale_y])
                            if len(scaled_points) >= 4:
                                canvas.create_line(scaled_points, fill=color, width=width, smooth=True, tags='annotation')
                    
                    elif ann_type == 'oval':
                        x1 = annotation['x1'] * scale_x
                        y1 = annotation['y1'] * scale_y
                        x2 = annotation['x2'] * scale_x
                        y2 = annotation['y2'] * scale_y
                        canvas.create_oval(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), 
                                         outline=color, width=width, tags='annotation')
                    
                    elif ann_type == 'rect':
                        x1 = annotation['x1'] * scale_x
                        y1 = annotation['y1'] * scale_y
                        x2 = annotation['x2'] * scale_x
                        y2 = annotation['y2'] * scale_y
                        canvas.create_rectangle(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), 
                                              outline=color, width=width, tags='annotation')
                    
                    elif ann_type == 'text':
                        x = annotation['x'] * scale_x
                        y = annotation['y'] * scale_y
                        text = annotation.get('text', '')
                        # 원본 폰트 크기 유지 (스케일링 제거)
                        font_size = annotation.get('font_size', 14)
                        bold = annotation.get('bold', False)  # 볼드 정보
                        
                        try:
                            # 🔥 안정적인 한글 폰트 사용 - 볼드 지원
                            font_name = self.font_manager.ui_font[0] if hasattr(self, 'font_manager') else '맑은 고딕'
                            font_weight = "bold" if bold else "normal"
                            font_tuple = (font_name, font_size, font_weight)
                            canvas.create_text(x, y, text=text, fill=color, font=font_tuple, 
                                             tags='annotation', anchor='nw')
                        except Exception as e:
                            # 폴백: 기본 폰트 사용
                            try:
                                font_tuple = (font_name, font_size)
                                canvas.create_text(x, y, text=text, fill=color, font=font_tuple, tags='annotation', anchor='nw')
                            except:
                                canvas.create_text(x, y, text=text, fill=color, tags='annotation', anchor='nw')
                    
                    elif ann_type == 'image':
                        x = annotation['x'] * scale_x
                        y = annotation['y'] * scale_y
                        width = annotation['width'] * scale_x
                        height = annotation['height'] * scale_y
                        
                        try:
                            # base64 이미지 디코딩
                            image_data = base64.b64decode(annotation['image_data'])
                            image = Image.open(io.BytesIO(image_data))
                            
                            # 반전 처리
                            if annotation.get('flip_horizontal', False):
                                image = image.transpose(Image.FLIP_LEFT_RIGHT)
                            if annotation.get('flip_vertical', False):
                                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                            
                            # 회전 처리 (크기 유지 개선)
                            rotation = annotation.get('rotation', 0)
                            if rotation != 0:
                                try:
                                    # 이미지를 RGBA 모드로 변환하여 투명도 지원
                                    if image.mode != 'RGBA':
                                        image = image.convert('RGBA')
                                    
                                    # 원본 크기 저장
                                    original_size = image.size
                                    
                                    # 투명 배경으로 회전 (expand=True로 잘림 방지)
                                    rotated_image = image.rotate(-rotation, expand=True, fillcolor=(0, 0, 0, 0))
                                    
                                    # 회전 후 크기와 원본 크기 비율 계산
                                    scale_factor = min(
                                        original_size[0] / rotated_image.size[0],
                                        original_size[1] / rotated_image.size[1]
                                    )
                                    
                                    # 회전된 이미지를 원본 크기에 맞게 조정
                                    if scale_factor < 1.0:
                                        # 회전으로 인해 크기가 커진 경우, 원본 크기에 맞게 스케일 다운
                                        temp_size = (
                                            int(rotated_image.size[0] * scale_factor),
                                            int(rotated_image.size[1] * scale_factor)
                                        )
                                        scaled_image = rotated_image.resize(temp_size, Image.Resampling.LANCZOS)
                                        
                                        # 원본 크기 캔버스에 중앙 배치
                                        image = Image.new('RGBA', original_size, (0, 0, 0, 0))
                                        paste_x = (original_size[0] - scaled_image.size[0]) // 2
                                        paste_y = (original_size[1] - scaled_image.size[1]) // 2
                                        image.paste(scaled_image, (paste_x, paste_y), scaled_image)
                                    else:
                                        # 회전 후에도 원본 크기보다 작은 경우, 중앙에 배치
                                        image = Image.new('RGBA', original_size, (0, 0, 0, 0))
                                        paste_x = (original_size[0] - rotated_image.size[0]) // 2
                                        paste_y = (original_size[1] - rotated_image.size[1]) // 2
                                        image.paste(rotated_image, (paste_x, paste_y), rotated_image)
                                    
                                    logger.debug(f"이미지 회전 완료 (크기 유지): {rotation}도, 원본={original_size}, 최종={image.size}")
                                    
                                except Exception as e:
                                    logger.error(f"이미지 회전 오류: {e}")
                                    # 폴백: 기본 회전
                                image = image.rotate(-rotation, expand=True)
                            
                            # 크기 조정 (이제 회전 후에도 원본 비율 유지됨)
                            display_image = image.resize((int(width), int(height)), Image.Resampling.LANCZOS)
                            
                            # 투명도 처리
                            opacity = annotation.get('opacity', 100) / 100.0
                            if opacity < 1.0:
                                # RGBA 모드로 변환
                                if display_image.mode != 'RGBA':
                                    display_image = display_image.convert('RGBA')
                                # 투명도 적용
                                alpha = display_image.split()[-1]
                                alpha = alpha.point(lambda p: p * opacity)
                                display_image.putalpha(alpha)
                            
                            # 🔥 아웃라인 처리 (ImageDraw로 완전한 테두리 - 두 번째)
                            if annotation.get('outline', False):
                                from PIL import ImageDraw
                                
                                # 아웃라인을 위한 이미지 확장
                                outline_width = annotation.get('outline_width', 3)
                                new_size = (display_image.width + outline_width * 2, 
                                           display_image.height + outline_width * 2)
                                outlined_image = Image.new('RGBA', new_size, (0, 0, 0, 0))
                                
                                # 🔥 ImageDraw로 확실한 흰색 아웃라인 그리기 (투명도 100% 안전)
                                draw = ImageDraw.Draw(outlined_image)
                                for i in range(outline_width):
                                    # 바깥쪽부터 안쪽까지 여러 겹의 흰색 테두리
                                    draw.rectangle([
                                        i, i, 
                                        outlined_image.width - 1 - i, 
                                        outlined_image.height - 1 - i
                                    ], outline=(255, 255, 255, 255), width=1)
                                
                                # 원본 이미지를 중앙에 붙이기 (RGBA 마스크 사용)
                                outlined_image.paste(display_image, (outline_width, outline_width), display_image if display_image.mode == 'RGBA' else None)
                                
                                display_image = outlined_image
                                x -= outline_width
                                y -= outline_width
                            
                            # tkinter용 이미지로 변환
                            photo = ImageTk.PhotoImage(display_image)
                            
                            # 캔버스에 그리기
                            image_id = canvas.create_image(x, y, image=photo, anchor='nw', tags='annotation image_annotation')
                            
                            # 이미지 참조 유지 (가비지 컬렉션 방지)
                            if not hasattr(canvas, 'annotation_images'):
                                canvas.annotation_images = {}
                            canvas.annotation_images[image_id] = photo
                            
                            # 이미지 주석을 최상단으로 올리기
                            canvas.tag_raise(image_id)
                            
                        except Exception as e:
                            logger.debug(f"이미지 주석 그리기 오류: {e}")
                            
                except Exception as e:
                    logger.debug(f"개별 주석 그리기 오류: {e}")
                    continue
            
            canvas.tag_raise('annotation', 'background')
            
        except Exception as e:
            logger.debug(f"주석 그리기 전체 오류: {e}")

    def update_canvas_size_and_image(self, canvas, item):
        """캔버스 크기와 이미지 업데이트"""
        try:
            # 현재 캔버스 크기 가져오기
            canvas.update_idletasks()
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            # 이미지 크기에 맞게 캔버스 크기 조정이 필요한지 확인
            image = item['image']
            
            # 이미지를 캔버스에 맞게 스케일링
            if canvas_width > 0 and canvas_height > 0:
                # 기존 배경 이미지 삭제
                canvas.delete('background')
                
                # 새 이미지를 캔버스에 표시
                image_ratio = image.width / image.height
                canvas_ratio = canvas_width / canvas_height
                
                if image_ratio > canvas_ratio:
                    # 이미지가 더 넓음 - 너비에 맞춤
                    display_width = canvas_width
                    display_height = int(canvas_width / image_ratio)
                else:
                    # 이미지가 더 높음 - 높이에 맞춤
                    display_height = canvas_height
                    display_width = int(canvas_height * image_ratio)
                
                # 이미지 리사이즈 및 표시 (투명도 지원 개선)
                display_image = image.resize((display_width, display_height), Image.Resampling.LANCZOS)
                
                # RGBA 이미지 처리 개선
                if display_image.mode == 'RGBA':
                    # 체커보드 배경 생성
                    checker_bg = self.create_checker_background(display_width, display_height)
                    # 투명 이미지를 체커보드 위에 합성
                    final_image = Image.alpha_composite(checker_bg, display_image)
                    canvas_image = ImageTk.PhotoImage(final_image)
                else:
                    canvas_image = ImageTk.PhotoImage(display_image)
                
                # 캔버스 중앙에 이미지 배치
                x = (canvas_width - display_width) // 2
                y = (canvas_height - display_height) // 2
                canvas.create_image(x, y, anchor='nw', image=canvas_image, tags='background')
                
                # 이미지 참조 유지 (가비지 컬렉션 방지)
                canvas.image = canvas_image
                
                logger.debug(f"캔버스 이미지 업데이트 완료: {display_width}x{display_height}")
            
        except Exception as e:
            logger.debug(f"캔버스 이미지 업데이트 오류: {e}")

    def create_checker_background(self, width, height, checker_size=16):
        """투명도 표시용 체커보드 배경 생성"""
        try:
            # RGBA 모드로 체커보드 생성
            checker_bg = Image.new('RGBA', (width, height), (255, 255, 255, 255))
            
            # 체커보드 패턴 그리기
            for y in range(0, height, checker_size):
                for x in range(0, width, checker_size):
                    # 격자 패턴으로 회색과 흰색 번갈아가며
                    if (x // checker_size + y // checker_size) % 2 == 0:
                        color = (220, 220, 220, 255)  # 연한 회색
                    else:
                        color = (255, 255, 255, 255)  # 흰색
                    
                    # 실제 체커 사각형 크기 계산
                    end_x = min(x + checker_size, width)
                    end_y = min(y + checker_size, height)
                    
                    # 픽셀별로 칠하기 (작은 영역이므로 속도 무관)
                    for py in range(y, end_y):
                        for px in range(x, end_x):
                            checker_bg.putpixel((px, py), color)
            
            return checker_bg
            
        except Exception as e:
            logger.debug(f"체커보드 배경 생성 오류: {e}")
            # 폴백: 흰 배경
            return Image.new('RGBA', (width, height), (255, 255, 255, 255))

    def redraw_canvas_annotations(self, canvas, item_index):
        """특정 캔버스의 주석만 다시 그리기"""
        try:
            if not (0 <= item_index < len(self.feedback_items)):
                return
            
            item = self.feedback_items[item_index]
            canvas.update_idletasks()
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            # 기존 주석 삭제
            canvas.delete('annotation')
            
            # 주석 다시 그리기
            self.draw_annotations(canvas, item, canvas_width, canvas_height)
            
            # 맨 뒤로 보내기
            canvas.tag_lower('background')
            canvas.update_idletasks()
            
            logger.debug(f"캔버스 주석 다시 그리기 완료: {item_index}")
            
        except Exception as e:
            logger.debug(f"캔버스 주석 다시 그리기 오류: {e}")

    def draw_annotations(self, canvas, item, canvas_width, canvas_height):
        """주석 그리기"""
        try:
            if not item or not canvas_width or not canvas_height:
                return
            
            scale_x = canvas_width / item['image'].width
            scale_y = canvas_height / item['image'].height
            
            for annotation in item['annotations']:
                try:
                    ann_type = annotation['type']
                    if ann_type == 'arrow':
                        x1 = annotation['start_x'] * scale_x
                        y1 = annotation['start_y'] * scale_y
                        x2 = annotation['end_x'] * scale_x
                        y2 = annotation['end_y'] * scale_y
                        color = annotation['color']
                        width = annotation['width']
                        # 🔥 개선된 화살표 그리기 사용
                        create_improved_arrow(canvas, x1, y1, x2, y2, color, width, 'annotation')
                    elif ann_type == 'line':
                        x1 = annotation['start_x'] * scale_x
                        y1 = annotation['start_y'] * scale_y
                        x2 = annotation['end_x'] * scale_x
                        y2 = annotation['end_y'] * scale_y
                        color = annotation['color']
                        width = annotation['width']
                        canvas.create_line(x1, y1, x2, y2, fill=color, width=width, tags='annotation')
                    elif ann_type == 'pen':
                        points = annotation.get('points', [])
                        if points:
                            scaled_points = [(x * scale_x, y * scale_y) for x, y in points]
                            color = annotation['color']
                            width = annotation['width']
                            canvas.create_line(scaled_points, fill=color, width=width, tags='annotation', smooth=True)
                    elif ann_type in ['oval', 'rect']:
                        x1 = annotation['x1'] * scale_x
                        y1 = annotation['y1'] * scale_y
                        x2 = annotation['x2'] * scale_x
                        y2 = annotation['y2'] * scale_y
                        color = annotation['color']
                        width = annotation['width']
                        if ann_type == 'oval':
                            canvas.create_oval(x1, y1, x2, y2, outline=color, width=width, tags='annotation')
                        else:
                            canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=width, tags='annotation')
                    
                    elif ann_type == 'text':
                        x = annotation['x'] * scale_x
                        y = annotation['y'] * scale_y
                        text = annotation.get('text', '')
                        # 🔥 스케일링된 폰트 크기 적용 - 메인 캔버스와 완전 동일
                        base_font_size = annotation.get('font_size', 14)
                        font_size = max(8, int(base_font_size * min(scale_x, scale_y)))
                        color = annotation['color']
                        # 🔥 맑은 고딕으로 통일
                        canvas.create_text(x, y, text=text, font=('맑은 고딕', font_size), fill=color, tags='annotation', anchor='nw')
                except Exception as e:
                    logger.debug(f"개별 주석 그리기 오류: {e}")
            
            logger.debug(f"주석 그리기 완료: {len(item['annotations'])}개")
            
        except Exception as e:
            logger.debug(f"주석 그리기 전체 오류: {e}")

    def add_pen_annotation(self, path_points, item, canvas_width, canvas_height, canvas):
        """펜 주석 추가"""
        try:
            if len(path_points) < 2:
                return
            
            scale_x = item['image'].width / canvas_width
            scale_y = item['image'].height / canvas_height
            
            scaled_points = [(x * scale_x, y * scale_y) for x, y in path_points]
            
            annotation = {
                'type': 'pen',
                'points': scaled_points,
                'color': self.annotation_color,
                'width': self.line_width
            }
            
            item['annotations'].append(annotation)
            logger.debug(f"펜 주석 추가: {len(scaled_points)}개 점")
            
            canvas.delete('annotation')
            self.draw_annotations(canvas, item, canvas_width, canvas_height)
            canvas.tag_lower('background')
            canvas.update_idletasks()
            
        except Exception as e:
            logger.debug(f"펜 주석 추가 오류: {e}")

    def add_arrow_annotation(self, start_x, start_y, end_x, end_y, item, canvas_width, canvas_height, canvas):
        """화살표 주석 추가"""
        try:
            if abs(end_x - start_x) < 5 and abs(end_y - start_y) < 5:
                return
            
            scale_x = item['image'].width / canvas_width
            scale_y = item['image'].height / canvas_height
            
            annotation = {
                'type': 'arrow',
                'start_x': start_x * scale_x,
                'start_y': start_y * scale_y,
                'end_x': end_x * scale_x,
                'end_y': end_y * scale_y,
                'color': self.annotation_color,
                'width': self.line_width
            }
            
            item['annotations'].append(annotation)
            logger.debug(f"화살표 주석 추가: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
            
            canvas.delete('annotation')
            self.draw_annotations(canvas, item, canvas_width, canvas_height)
            canvas.tag_lower('background')
            canvas.update_idletasks()
            
        except Exception as e:
            logger.debug(f"화살표 주석 추가 오류: {e}")

    def add_shape_annotation(self, shape, x1, y1, x2, y2, item, cw, ch, canvas):
        """원형·사각형 주석 추가"""
        try:
            if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
                return
            
            scale_x = item['image'].width / cw
            scale_y = item['image'].height / ch
            
            annotation = {
                'type': shape,
                'x1': x1 * scale_x,
                'y1': y1 * scale_y,
                'x2': x2 * scale_x,
                'y2': y2 * scale_y,
                'color': self.annotation_color,
                'width': self.line_width
            }
            
            item['annotations'].append(annotation)
            logger.debug(f"{shape} 주석 추가: ({x1}, {y1}) -> ({x2}, {y2})")
            
            canvas.delete('annotation')
            self.draw_annotations(canvas, item, cw, ch)
            canvas.tag_lower('background')
            canvas.update_idletasks()
            
        except Exception as e:
            logger.debug(f"{shape} 주석 추가 오류: {e}")

    def annotation_in_rect(self, annotation, min_x, min_y, max_x, max_y):
        """주석이 사각형 영역 안에 있는지 확인"""
        if not annotation or not isinstance(annotation, dict):
            logger.debug("유효하지 않은 주석 데이터")
            return False
        try:
            ann_type = annotation['type']
            if ann_type == 'arrow':
                x1, y1 = annotation['start_x'], annotation['start_y']
                x2, y2 = annotation['end_x'], annotation['end_y']
                return (min_x <= x1 <= max_x and min_y <= y1 <= max_y) or \
                       (min_x <= x2 <= max_x and min_y <= y2 <= max_y)
            elif ann_type == 'line':
                # 라인도 화살표와 동일한 방식으로 처리
                x1, y1 = annotation['start_x'], annotation['start_y']
                x2, y2 = annotation['end_x'], annotation['end_y']
                return (min_x <= x1 <= max_x and min_y <= y1 <= max_y) or \
                       (min_x <= x2 <= max_x and min_y <= y2 <= max_y)
            elif ann_type == 'pen':
                points = annotation.get('points', [])
                for x, y in points:
                    if min_x <= x <= max_x and min_y <= y <= max_y:
                        return True
                return False
            elif ann_type in ['oval', 'rect']:
                x1, y1 = annotation['x1'], annotation['y1']
                x2, y2 = annotation['x2'], annotation['y2']
                return (min_x <= x1 <= max_x and min_y <= y1 <= max_y) or \
                       (min_x <= x2 <= max_x and min_y <= y2 <= max_y)
            elif ann_type == 'text':
                x, y = annotation['x'], annotation['y']
                text = annotation.get('text', '')
                font_size = annotation.get('font_size', 14)
                # 텍스트 영역 계산 (anchor='nw' 기준, 클릭 영역과 동일하게)
                text_width = max(len(text) * font_size * 0.7, 60)
                text_height = max(font_size * 1.5, 25)
                margin = 15
                # nw 앵커 기준으로 확장된 영역에서의 교차 검사
                return not (x + text_width + margin < min_x or x - margin > max_x or 
                           y + text_height + margin < min_y or y - margin > max_y)
            elif ann_type == 'image':
                x, y = annotation['x'], annotation['y']
                width = annotation['width']
                height = annotation['height']
                # 이미지 영역이 선택 영역과 교차하는지 확인
                return not (x + width < min_x or x > max_x or 
                            y + height < min_y or y > max_y)
            return False
        except Exception as e:
            logger.debug(f"주석 영역 확인 오류: {e}")
            return False

    def highlight_selected_annotations(self, canvas, canvas_width, canvas_height):
        """선택된 주석들을 하이라이트 표시"""
        try:
            # 기존 하이라이트 제거
            canvas.delete('highlight')
            if not self.selected_annotations:
                return
            # 현재 선택된 항목 확인
            if not (0 <= self.current_index < len(self.feedback_items)):
                return
            item = self.feedback_items[self.current_index]
            scale_x = canvas_width / item['image'].width
            scale_y = canvas_height / item['image'].height
            # 선택된 각 주석에 대해 하이라이트 그리기
            for annotation in self.selected_annotations:
                try:
                    ann_type = annotation['type']
                    if ann_type == 'arrow':
                        x1 = annotation['start_x'] * scale_x
                        y1 = annotation['start_y'] * scale_y
                        x2 = annotation['end_x'] * scale_x
                        y2 = annotation['end_y'] * scale_y
                        # 화살표 주변에 하이라이트 박스
                        margin = 10
                        canvas.create_rectangle(
                            min(x1, x2) - margin, min(y1, y2) - margin,
                            max(x1, x2) + margin, max(y1, y2) + margin,
                            outline='lime', width=3, dash=(3, 3), tags='highlight'
                        )
                    elif ann_type == 'line':
                        # 라인도 화살표와 동일한 방식으로 하이라이트
                        x1 = annotation['start_x'] * scale_x
                        y1 = annotation['start_y'] * scale_y
                        x2 = annotation['end_x'] * scale_x
                        y2 = annotation['end_y'] * scale_y
                        # 라인 주변에 하이라이트 박스
                        margin = 10
                        canvas.create_rectangle(
                            min(x1, x2) - margin, min(y1, y2) - margin,
                            max(x1, x2) + margin, max(y1, y2) + margin,
                            outline='lime', width=3, dash=(3, 3), tags='highlight'
                        )
                    elif ann_type == 'pen':
                        points = annotation.get('points', [])
                        if points:
                            # 펜 경로의 바운딩 박스 계산
                            scaled_points = [(x * scale_x, y * scale_y) for x, y in points]
                            min_x = min(p[0] for p in scaled_points)
                            max_x = max(p[0] for p in scaled_points)
                            min_y = min(p[1] for p in scaled_points)
                            max_y = max(p[1] for p in scaled_points)
                            margin = 10
                            canvas.create_rectangle(
                                min_x - margin, min_y - margin,
                                max_x + margin, max_y + margin,
                                outline='lime', width=3, dash=(3, 3), tags='highlight'
                            )
                    elif ann_type in ['oval', 'rect']:
                        x1 = annotation['x1'] * scale_x
                        y1 = annotation['y1'] * scale_y
                        x2 = annotation['x2'] * scale_x
                        y2 = annotation['y2'] * scale_y
                        margin = 5
                        canvas.create_rectangle(
                            min(x1, x2) - margin, min(y1, y2) - margin,
                            max(x1, x2) + margin, max(y1, y2) + margin,
                            outline='lime', width=3, dash=(3, 3), tags='highlight'
                        )
                    elif ann_type == 'text':
                        x = annotation['x'] * scale_x
                        y = annotation['y'] * scale_y
                        text = annotation.get('text', '')
                        # 원본 폰트 크기 유지 (하이라이트용)
                        font_size = annotation.get('font_size', 14)
                        # 텍스트 크기 추정 (anchor='nw' 기준, 클릭 영역과 동일하게)
                        text_width = max(len(text) * font_size * 0.7, 60)
                        text_height = max(font_size * 1.5, 25)
                        margin = 15  # 클릭 영역과 동일한 마진
                        canvas.create_rectangle(
                            x - margin, y - margin,
                            x + text_width + margin, y + text_height + margin,
                            outline='lime', width=3, dash=(3, 3), tags='highlight'
                        )
                    elif ann_type == 'image':
                        x = annotation['x'] * scale_x
                        y = annotation['y'] * scale_y
                        width = annotation['width'] * scale_x
                        height = annotation['height'] * scale_y
                        margin = 5
                        canvas.create_rectangle(
                            x - margin, y - margin,
                            x + width + margin, y + height + margin,
                            outline='lime', width=3, dash=(3, 3), tags='highlight'
                        )
                except Exception as e:
                    logger.debug(f"개별 주석 하이라이트 오류: {e}")
            # 하이라이트를 맨 위로
            canvas.tag_raise('highlight')
        except Exception as e:
            logger.debug(f"주석 하이라이트 오류: {e}")

    def delete_selected_annotations(self):
        """선택된 주석들 삭제"""
        try:
            if not self.selected_annotations:
                self.update_status_message("선택된 주석이 없습니다")
                return
            
            if not (0 <= self.current_index < len(self.feedback_items)):
                self.update_status_message("유효하지 않은 항목입니다")
                return
            
            item = self.feedback_items[self.current_index]
            
            # 실행 취소를 위한 상태 저장
            self.undo_manager.save_state(item['id'], item['annotations'])
            
            # 선택된 주석들을 annotations 리스트에서 제거
            original_count = len(item['annotations'])
            item['annotations'] = [ann for ann in item['annotations'] if ann not in self.selected_annotations]
            deleted_count = original_count - len(item['annotations'])
            
            # 선택 해제 (선택 사각형 포함)
            self.clear_selection()
            
            # 모든 캔버스에서 선택 관련 요소 강제 제거
            try:
                if hasattr(self, 'scrollable_frame') and self.scrollable_frame.winfo_exists():
                    for widget in self.scrollable_frame.winfo_children():
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Frame):
                                for grandchild in child.winfo_children():
                                    if isinstance(grandchild, tk.Canvas):
                                        try:
                                            grandchild.delete('highlight')
                                            grandchild.delete('selection_rect')
                                            grandchild.delete('drawing_temp')
                                        except:
                                            pass
            except:
                pass
            
            # 화면 새로고침
            self.refresh_current_item()
            
            # 상태 메시지 업데이트
            self.update_status_message(f"{deleted_count}개 주석이 삭제되었습니다")
            
            logger.info(f"선택된 주석 삭제 완료: {deleted_count}개")
                
        except Exception as e:
            logger.error(f"선택된 주석 삭제 오류: {e}")
            self.update_status_message("주석 삭제 중 오류가 발생했습니다")

    def edit_annotation_image(self, annotation):
        """이미지 주석 편집 다이얼로그 (실시간 반영)"""
        dialog = tk.Toplevel(self.root)
        dialog.title("이미지 주석 편집 - 실시간 미리보기")
        
        # 🔥 아이콘 설정
        setup_window_icon(dialog)
        
        dialog.geometry("420x650")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 중앙 정렬
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        main_frame = tk.Frame(dialog, padx=20, pady=20, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 실시간 업데이트를 위한 변수들 저장
        original_values = {
            'width': annotation['width'],
            'height': annotation['height'],
            'opacity': annotation.get('opacity', 100),
            'outline': annotation.get('outline', False),
            'outline_width': annotation.get('outline_width', 3),
            'flip_horizontal': annotation.get('flip_horizontal', False),
            'flip_vertical': annotation.get('flip_vertical', False),
            'rotation': annotation.get('rotation', 0)
        }
        
        # 실시간 업데이트 함수
        def apply_realtime_changes():
            """변경사항을 실시간으로 적용"""
            try:
                # 변경사항을 annotation에 즉시 적용
                annotation['width'] = width_var.get()
                annotation['height'] = height_var.get()
                annotation['opacity'] = opacity_var.get()
                annotation['outline'] = outline_var.get()
                annotation['outline_width'] = outline_width_var.get()
                annotation['flip_horizontal'] = flip_h_var.get()
                annotation['flip_vertical'] = flip_v_var.get()
                annotation['rotation'] = rotation_var.get()
                
                # 현재 화면 즉시 새로고침
                self.refresh_current_item()
                
            except Exception as e:
                print(f"실시간 업데이트 오류: {e}")
        
        # 원래 값으로 되돌리는 함수
        def restore_original_values():
            """취소 시 원래 값으로 복원"""
            for key, value in original_values.items():
                annotation[key] = value
            self.refresh_current_item()
        
        # 크기 조정
        size_frame = tk.LabelFrame(main_frame, text="크기", bg='white', 
                                  font=self.font_manager.ui_font)
        size_frame.pack(fill=tk.X, pady=(0, 15))
        
        size_inner = tk.Frame(size_frame, bg='white')
        size_inner.pack(padx=10, pady=10)
        
        tk.Label(size_inner, text="너비:", bg='white').grid(row=0, column=0, sticky='e', padx=5)
        width_var = tk.IntVar(value=annotation['width'])
        width_spin = tk.Spinbox(size_inner, from_=10, to=2000, textvariable=width_var, width=10)
        width_spin.grid(row=0, column=1, padx=5)
        
        tk.Label(size_inner, text="높이:", bg='white').grid(row=1, column=0, sticky='e', padx=5)
        height_var = tk.IntVar(value=annotation['height'])
        height_spin = tk.Spinbox(size_inner, from_=10, to=2000, textvariable=height_var, width=10)
        height_spin.grid(row=1, column=1, padx=5)
        
        # 비율 유지 체크박스
        maintain_ratio = tk.BooleanVar(value=True)
        tk.Checkbutton(size_inner, text="비율 유지", variable=maintain_ratio, 
                       bg='white').grid(row=2, column=0, columnspan=2, pady=5)
        
        # 빠른 크기 조정 버튼들
        quick_size_frame = tk.Frame(size_inner, bg='white')
        quick_size_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        tk.Label(quick_size_frame, text="빠른 크기 조정:", bg='white').pack(anchor='w')
        
        button_frame = tk.Frame(quick_size_frame, bg='white')
        button_frame.pack(fill=tk.X, pady=5)
        
        # 원본 크기 저장 (최초 이미지 크기)
        original_width = annotation.get('original_width', annotation['width'])
        original_height = annotation.get('original_height', annotation['height'])
        annotation['original_width'] = original_width
        annotation['original_height'] = original_height
        
        # 원본 비율 저장
        original_ratio = original_width / original_height
        
        def resize_to_percent(percent):
            """지정된 퍼센트로 크기 조정 (실시간 반영)"""
            new_width = int(original_width * percent / 100)
            new_height = int(original_height * percent / 100)
            width_var.set(new_width)
            height_var.set(new_height)
            # 실시간 반영
            dialog.after(10, apply_realtime_changes)
        
        # 크기 조정 버튼들
        tk.Button(button_frame, text="25%", command=lambda: resize_to_percent(25),
                 bg='lightblue', relief='groove', width=6).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="50%", command=lambda: resize_to_percent(50),
                 bg='lightblue', relief='groove', width=6).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="100%", command=lambda: resize_to_percent(100),
                 bg='lightgreen', relief='groove', width=6).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="150%", command=lambda: resize_to_percent(150),
                 bg='lightblue', relief='groove', width=6).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="200%", command=lambda: resize_to_percent(200),
                 bg='lightblue', relief='groove', width=6).pack(side=tk.LEFT, padx=2)
        
        def on_width_change():
            if maintain_ratio.get():
                new_height = int(width_var.get() / original_ratio)
                height_var.set(new_height)
            # 실시간 반영
            dialog.after(100, apply_realtime_changes)
        
        def on_height_change():
            if maintain_ratio.get():
                new_width = int(height_var.get() * original_ratio)
                width_var.set(new_width)
            # 실시간 반영
            dialog.after(100, apply_realtime_changes)
        
        # 변수 변경 추적으로 실시간 비율 유지 및 반영
        width_var.trace('w', lambda *args: on_width_change())
        height_var.trace('w', lambda *args: on_height_change())
        
        # 투명도
        opacity_frame = tk.LabelFrame(main_frame, text="투명도", bg='white',
                                     font=self.font_manager.ui_font)
        opacity_frame.pack(fill=tk.X, pady=(0, 15))
        
        opacity_var = tk.IntVar(value=annotation.get('opacity', 100))
        opacity_label = tk.Label(opacity_frame, text=f"{opacity_var.get()}%", bg='white')
        opacity_label.pack()
        
        def update_opacity_label(value):
            opacity_label.config(text=f"{int(float(value))}%")
            # 실시간 반영
            dialog.after(50, apply_realtime_changes)
        
        opacity_scale = tk.Scale(opacity_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                variable=opacity_var, command=update_opacity_label,
                                bg='white', length=300, 
                                activebackground='lightblue', troughcolor='lightgray')
        opacity_scale.pack(padx=10, pady=5)
        
        # 아웃라인
        outline_frame = tk.LabelFrame(main_frame, text="아웃라인", bg='white',
                                     font=self.font_manager.ui_font)
        outline_frame.pack(fill=tk.X, pady=(0, 15))
        
        outline_inner = tk.Frame(outline_frame, bg='white')
        outline_inner.pack(padx=10, pady=10)
        
        outline_var = tk.BooleanVar(value=annotation.get('outline', False))
        
        def on_outline_change():
            dialog.after(50, apply_realtime_changes)
        
        def on_outline_width_change():
            dialog.after(100, apply_realtime_changes)
        
        tk.Checkbutton(outline_inner, text="흰색 아웃라인 사용", variable=outline_var,
                       bg='white', command=on_outline_change).pack(anchor='w')
        
        tk.Label(outline_inner, text="두께:", bg='white').pack(side=tk.LEFT, padx=(20, 5))
        outline_width_var = tk.IntVar(value=annotation.get('outline_width', 3))
        outline_width_spin = tk.Spinbox(outline_inner, from_=1, to=10, textvariable=outline_width_var,
                                       width=5, command=on_outline_width_change)
        outline_width_spin.pack(side=tk.LEFT)
        
        # outline_width_var 변경 추적
        outline_width_var.trace('w', lambda *args: on_outline_width_change())
        
        # 변형
        transform_frame = tk.LabelFrame(main_frame, text="변형", bg='white',
                                       font=self.font_manager.ui_font)
        transform_frame.pack(fill=tk.X, pady=(0, 15))
        
        transform_inner = tk.Frame(transform_frame, bg='white')
        transform_inner.pack(padx=10, pady=10)
        
        flip_h_var = tk.BooleanVar(value=annotation.get('flip_horizontal', False))
        flip_v_var = tk.BooleanVar(value=annotation.get('flip_vertical', False))
        
        def on_flip_change():
            dialog.after(50, apply_realtime_changes)
        
        def on_rotation_change():
            dialog.after(100, apply_realtime_changes)
        
        tk.Checkbutton(transform_inner, text="좌우 반전", variable=flip_h_var,
                       bg='white', command=on_flip_change).pack(anchor='w')
        tk.Checkbutton(transform_inner, text="상하 반전", variable=flip_v_var,
                       bg='white', command=on_flip_change).pack(anchor='w')
        
        # 회전
        rotation_frame = tk.Frame(transform_inner, bg='white')
        rotation_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Label(rotation_frame, text="회전 각도:", bg='white').pack(side=tk.LEFT, padx=(0, 5))
        rotation_var = tk.IntVar(value=annotation.get('rotation', 0))
        rotation_spin = tk.Spinbox(rotation_frame, from_=-180, to=180, textvariable=rotation_var,
                                  width=5, command=on_rotation_change)
        rotation_spin.pack(side=tk.LEFT)
        tk.Label(rotation_frame, text="도", bg='white').pack(side=tk.LEFT)
        
        # rotation_var 변경 추적
        rotation_var.trace('w', lambda *args: on_rotation_change())
        
        # 실행 취소를 위한 상태 저장 (편집 시작 시)
        current_item = self.feedback_items[self.current_index]
        self.undo_manager.save_state(current_item['id'], current_item['annotations'])
        
        # 실시간 미리보기 상태 표시
        status_frame = tk.Frame(main_frame, bg='lightblue', relief='raised', bd=1)
        status_frame.pack(fill=tk.X, pady=(10, 10))
        
        status_label = tk.Label(status_frame, text="✨ 실시간 미리보기 활성화 - 변경사항이 즉시 반영됩니다", 
                               bg='lightblue', fg='darkblue', font=('Arial', 9, 'bold'))
        status_label.pack(pady=5)
        
        # 버튼
        button_frame = tk.Frame(main_frame, bg='white')
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def apply_and_close():
            """변경사항을 확정하고 다이얼로그 닫기"""
            dialog.destroy()
            self.update_status_message("이미지 주석이 수정되었습니다")
        
        def cancel_and_restore():
            """변경사항을 취소하고 원래 값으로 복원"""
            restore_original_values()
            dialog.destroy()
            self.update_status_message("이미지 편집이 취소되었습니다")
        
        # 버튼 스타일
        button_style = {
            'font': ('Arial', 10, 'bold'),
            'relief': 'flat',
            'height': 2,
            'cursor': 'hand2'
        }
        
        # 취소 버튼
        cancel_btn = tk.Button(button_frame, text="❌ 취소", command=cancel_and_restore,
                              bg='#f44336', fg='white', width=12, **button_style)
        cancel_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 확정 버튼  
        apply_btn = tk.Button(button_frame, text="✅ 확정", command=apply_and_close,
                             bg='#4CAF50', fg='white', width=12, **button_style)
        apply_btn.pack(side=tk.RIGHT)
        
        # Esc 키로 취소
        dialog.bind('<Escape>', lambda e: cancel_and_restore())
        
        # 포커스 설정
        dialog.focus_set()

    def show_custom_text_dialog(self, initial_text="", initial_font_size=None, initial_color=None, initial_bold=None):
        """커스텀 텍스트 입력 대화상자 - 스크롤 기능 개선"""
        try:
            logger.info(f"📝 텍스트 입력 다이얼로그 시작: 초기값='{initial_text}', 크기={initial_font_size}, 색상={initial_color}")
            logger.info("📝 다이얼로그 호출 스택 확인")
            dialog = tk.Toplevel(self.root)
            dialog.title("텍스트 입력")
            
            # 🔥 아이콘 설정
            setup_window_icon(dialog)
            
            # 🔥 창 크기 개선 - 스크롤을 고려한 적응형 크기
            screen_width = dialog.winfo_screenwidth()
            screen_height = dialog.winfo_screenheight()
            
            # 기본 크기 계산 (화면 크기의 35% 너비, 70% 높이, 최소/최대 제한)
            dialog_width = max(550, min(700, int(screen_width * 0.35)))
            dialog_height = max(500, min(800, int(screen_height * 0.7)))
            
            dialog.geometry(f"{dialog_width}x{dialog_height}")
            dialog.resizable(True, True)
            dialog.minsize(500, 450)  # 최소 크기 설정
            dialog.maxsize(int(screen_width * 0.8), int(screen_height * 0.9))  # 최대 크기 설정
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 🔥 스마트 창 위치 조정 - 화면 경계 고려
            dialog.update_idletasks()
            
            try:
                parent_x = self.root.winfo_x()
                parent_y = self.root.winfo_y()
                parent_width = self.root.winfo_width()
                parent_height = self.root.winfo_height()
                
                # 부모 창 중앙 계산
                x = parent_x + (parent_width - dialog_width) // 2
                y = parent_y + (parent_height - dialog_height) // 2
            except tk.TclError:
                # 부모 창 정보를 가져올 수 없는 경우 화면 중앙으로
                x = (screen_width - dialog_width) // 2
                y = (screen_height - dialog_height) // 2
            
            # 화면 경계 확인 및 조정
            margin = 20
            if x + dialog_width > screen_width - margin:
                x = screen_width - dialog_width - margin
            if x < margin:
                x = margin
            if y + dialog_height > screen_height - 60:  # 작업 표시줄 고려
                y = screen_height - dialog_height - 60
            if y < margin:
                y = margin
            
            dialog.geometry(f"+{x}+{y}")
            
            # 🔥 상단 고정 영역 (설정 컨트롤)
            top_frame = tk.Frame(dialog, bg='white', relief='ridge', bd=1)
            top_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
            
            # 🔥 하단 고정 영역 (버튼)
            bottom_frame = tk.Frame(dialog, bg='white', relief='ridge', bd=1)
            bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 10))
            
            # 🔥 중앙 스크롤 영역 (텍스트 입력)
            middle_container = tk.Frame(dialog)
            middle_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # 캔버스와 스크롤바 (텍스트 입력 영역만)
            text_canvas = tk.Canvas(middle_container, bg='white', highlightthickness=1, highlightbackground='#ddd')
            text_scrollbar = tk.Scrollbar(middle_container, orient="vertical", command=text_canvas.yview)
            text_scrollable_frame = tk.Frame(text_canvas, bg='white')
            
            # 스크롤바 설정
            text_scrollable_frame.bind(
                "<Configure>",
                lambda e: text_canvas.configure(scrollregion=text_canvas.bbox("all"))
            )
            
            text_canvas.create_window((0, 0), window=text_scrollable_frame, anchor="nw")
            text_canvas.configure(yscrollcommand=text_scrollbar.set)
            
            # 마우스 휠 스크롤 지원
            def _on_mousewheel(event):
                text_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            text_canvas.bind("<MouseWheel>", _on_mousewheel)
            
            # 스크롤바와 캔버스 배치
            text_canvas.pack(side="left", fill="both", expand=True)
            text_scrollbar.pack(side="right", fill="y")
            
            # 실제 텍스트 입력이 들어갈 프레임
            text_input_frame = tk.Frame(text_scrollable_frame, bg='white', padx=20, pady=20)
            text_input_frame.pack(fill=tk.BOTH, expand=True)
            
            # 🔥 상단 텍스트 설정 섹션 (고정)
            tk.Label(top_frame, text="텍스트 설정:", bg='white',
                    font=self.font_manager.ui_font_bold).pack(anchor=tk.W, pady=(10, 5), padx=10)
            
            # 설정 컨트롤 프레임 (상단 고정)
            controls_frame = tk.Frame(top_frame, bg='white')
            controls_frame.pack(fill=tk.X, pady=(0, 10), padx=10)
            
            # 🔥 폰트 크기 설정
            font_size_frame = tk.Frame(controls_frame, bg='white')
            font_size_frame.pack(side=tk.LEFT, padx=(0, 20))
            
            tk.Label(font_size_frame, text="크기:", bg='white', font=self.font_manager.ui_font_small).pack(anchor=tk.W)
            
            # 🔥 초기값 설정 (편집 시 기존 값 사용)
            text_font_size = [initial_font_size if initial_font_size else self.font_size]
            
            font_size_label = tk.Label(font_size_frame, text=f"{text_font_size[0]}px", 
                                     bg='white', font=self.font_manager.ui_font_small, fg='#666')
            font_size_label.pack()
            
            font_size_scale = tk.Scale(font_size_frame, from_=8, to=96, 
                                     orient=tk.HORIZONTAL, length=120,
                                     bg='white', font=self.font_manager.ui_font_small,
                                     highlightthickness=0, bd=0, showvalue=0)
            font_size_scale.set(text_font_size[0])
            font_size_scale.pack()
            
            # 🔥 텍스트 색상 설정
            color_frame = tk.Frame(controls_frame, bg='white')
            color_frame.pack(side=tk.LEFT, padx=(0, 20))
            
            tk.Label(color_frame, text="색상:", bg='white', font=self.font_manager.ui_font_small).pack(anchor=tk.W)
            
            text_color = [initial_color if initial_color else self.annotation_color]
            
            color_button = tk.Button(color_frame, text="  ", bg=text_color[0], 
                                   width=8, height=1, relief='solid', bd=2)
            color_button.pack(pady=(5, 0))
            
            # 🔥 볼드 설정 추가
            bold_frame = tk.Frame(controls_frame, bg='white')
            bold_frame.pack(side=tk.LEFT)
            
            tk.Label(bold_frame, text="스타일:", bg='white', font=self.font_manager.ui_font_small).pack(anchor=tk.W)
            
            text_bold = [initial_bold if initial_bold is not None else False]  # 볼드 상태 저장
            
            bold_button = tk.Button(bold_frame, text="B", 
                                  font=(self.font_manager.ui_font[0], 12, "bold"), 
                                  width=3, height=1, relief='raised', bd=2,
                                  bg='#f0f0f0')
            bold_button.pack(pady=(5, 0))
            
            # 🔥 초기 볼드 상태 반영
            if text_bold[0]:
                bold_button.config(relief='sunken', bg='#e0e0e0')
            
            # 안내 텍스트 (텍스트 입력 영역 상단)
            tk.Label(text_input_frame, text="텍스트 내용:", bg='white',
                    font=self.font_manager.ui_font).pack(anchor=tk.W, pady=(0, 5))
            
            # 텍스트 입력 영역 (여러 줄 가능)
            text_frame = tk.Frame(text_input_frame, bg='white')
            text_frame.pack(fill=tk.BOTH, expand=True)
            
            # 🔥 피드백 입력창과 완전 동일한 안정적인 폰트 설정 (조합 안정화)
            # 시스템에서 사용 가능한 한글 폰트 우선순위로 설정
            stable_font = (self.font_manager.ui_font[0], 'Malgun Gothic', '맑은 고딕', 'Arial Unicode MS')  # 안정적인 폰트 우선순위
            
            text_widget = tk.Text(text_frame, height=8, wrap=tk.WORD, 
                                 font=(stable_font, text_font_size[0]), relief='flat', bd=1,
                                 highlightthickness=2, highlightcolor='#6c757d',
                                 insertwidth=2,  # 🔥 커서 너비 고정
                                 insertborderwidth=0,  # 🔥 커서 테두리 제거
                                 insertofftime=300,  # 🔥 커서 깜빡임 조정
                                 insertontime=600,   # 🔥 커서 표시 시간 조정
                                 fg=text_color[0])   # 🔥 텍스트 색상 적용
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # 🔥 폰트 적용 함수
            def apply_font():
                """현재 설정에 따라 폰트 적용"""
                font_style = "bold" if text_bold[0] else "normal"
                current_font = (stable_font[0], text_font_size[0], font_style)
                text_widget.config(font=current_font)
                # 전체 텍스트에 새 폰트 적용
                text_widget.tag_add('all', '1.0', 'end')
                text_widget.tag_configure('all', font=current_font, foreground=text_color[0])
            
            # 🔥 실시간 폰트 크기 변경
            def update_font_size(value):
                new_size = int(float(value))
                text_font_size[0] = new_size
                font_size_label.config(text=f"{new_size}px")
                apply_font()
            
            font_size_scale.config(command=update_font_size)
            
            # 🔥 볼드 토글 기능
            def toggle_bold():
                text_bold[0] = not text_bold[0]
                if text_bold[0]:
                    bold_button.config(relief='sunken', bg='#e0e0e0')
                else:
                    bold_button.config(relief='raised', bg='#f0f0f0')
                apply_font()
            
            bold_button.config(command=toggle_bold)
            
            # 🔥 실시간 색상 변경
            def update_text_color():
                color = colorchooser.askcolor(color=text_color[0], title="텍스트 색상 선택")[1]
                if color:
                    text_color[0] = color
                    color_button.config(bg=color)
                    text_widget.config(fg=color)
                    apply_font()  # 볼드 상태를 유지하면서 색상 적용
            
            color_button.config(command=update_text_color)
            
            # 🔥 한글 조합 중 안정적인 표시를 위한 고급 설정
            try:
                # 일관된 폰트 렌더링을 위한 설정
                text_widget.configure(
                    spacing1=0,  # 줄 위 간격 고정
                    spacing2=0,  # 줄 사이 간격 고정  
                    spacing3=0,  # 줄 아래 간격 고정
                    selectborderwidth=0,  # 선택 테두리 제거
                    selectforeground='black',  # 선택 시 글자색 고정
                    selectbackground='lightblue'  # 선택 배경색 고정
                )
                # 태그 기반 일관된 폰트 적용
                text_widget.tag_configure('all', font=(stable_font, text_font_size[0]), foreground=text_color[0])
                text_widget.tag_add('all', '1.0', 'end')
                # IME 조합창 설정
                text_widget.tk.call('tk::imestatus', text_widget, 'on')
            except:
                pass
            
            # 스크롤바
            scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, 
                                   command=text_widget.yview, width=16)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            # 🔥 초기 텍스트 설정 (편집 모드)
            if initial_text:
                text_widget.insert('1.0', initial_text)
                text_widget.focus_set()
                # 처음에는 전체 텍스트 선택
                text_widget.tag_add(tk.SEL, '1.0', tk.END)
                text_widget.mark_set(tk.INSERT, '1.0')
                # 초기 폰트 적용
                apply_font()
            
            # 결과 저장 변수
            result = [None]
            
            def on_ok():
                text_content = text_widget.get('1.0', tk.END).strip()
                if text_content:
                    # 🔥 텍스트와 함께 폰트 설정도 반환 (볼드 정보 포함)
                    result[0] = {
                        'text': text_content,
                        'font_size': text_font_size[0],
                        'color': text_color[0],
                        'bold': text_bold[0]
                    }
                else:
                    result[0] = None
                dialog.destroy()
            
            def on_cancel():
                result[0] = None
                dialog.destroy()
            
            # 🔥 하단 고정 버튼들 (항상 보임)
            button_container = tk.Frame(bottom_frame, bg='white')
            button_container.pack(fill=tk.X, pady=10, padx=10)
            
            tk.Button(button_container, text="❌ 취소", command=on_cancel,
                     font=self.font_manager.ui_font, width=12, height=2,
                     bg='#f44336', fg='white', relief='flat', bd=0, 
                     cursor='hand2').pack(side=tk.LEFT)
            
            tk.Button(button_container, text="✅ 확인", command=on_ok,
                     font=self.font_manager.ui_font, width=12, height=2,
                     bg='#4CAF50', fg='white', relief='flat', bd=0,
                     cursor='hand2').pack(side=tk.RIGHT)
            
            # 키보드 단축키 및 폰트 일관성 유지
            def handle_shortcuts(event):
                # 🔥 한글 조합 중 폰트 일관성 유지
                try:
                    text_widget.tag_add('all', '1.0', 'end')
                    text_widget.tag_configure('all', font=(stable_font, text_font_size[0]), foreground=text_color[0])
                except:
                    pass
                    
                if event.state & 0x4 and event.keysym == 'Return':  # Ctrl+Enter
                    on_ok()
                    return "break"
                return None
            
            text_widget.bind('<KeyPress>', handle_shortcuts)
            dialog.bind('<Escape>', lambda e: on_cancel())
            
            # 🔥 초기 텍스트 설정
            if initial_text:
                text_widget.insert('1.0', initial_text)
                text_widget.tag_add('all', '1.0', 'end')
                text_widget.tag_configure('all', font=(stable_font, text_font_size[0]), foreground=text_color[0])
            
            # 🔥 텍스트 입력 상태 개선
            text_widget.config(state='normal')  # 입력 가능 상태 명시적 설정
            text_widget.config(insertborderwidth=1)  # 커서 표시 개선
            
            # 🔥 텍스트 변경 시 폰트 일관성 유지 (디버그 로그 제거)
            def on_text_change(event=None):
                try:
                    # 텍스트 변경 시 폰트 일관성 유지 (디버그 로그 완전 제거)
                    content = text_widget.get('1.0', 'end-1c')
                    if content:
                        text_widget.tag_add('all', '1.0', 'end')
                        text_widget.tag_configure('all', font=(stable_font, text_font_size[0]), foreground=text_color[0])
                except Exception:
                    # 로그 출력 완전 제거
                    pass
            
            # 텍스트 변경 이벤트 바인딩
            text_widget.bind('<KeyRelease>', on_text_change)
            
            # 포커스 및 커서 위치 설정
            dialog.after(100, lambda: (
                text_widget.focus_force(),
                text_widget.mark_set(tk.INSERT, '1.0'),
                text_widget.see(tk.INSERT)
            ))
            
            # 대화상자 대기
            logger.info("📝 텍스트 다이얼로그 대기 시작")
            dialog.wait_window()
            
            logger.info(f"📝 텍스트 다이얼로그 종료, 결과: {result[0]}")
            return result[0]
            
        except Exception as e:
            logger.error(f"커스텀 텍스트 대화상자 오류: {e}")
            from tkinter import simpledialog
            return simpledialog.askstring('텍스트 입력', '텍스트를 입력하세요:')

    def test_annotation_system(self):
        """주석 시스템 테스트"""
        if not ('--debug' in sys.argv or os.getenv('DEBUG_MODE') == '1'):
            return  # 디버그 모드가 아니면 테스트 실행하지 않음
            
        logger.debug("🧪 주석 시스템 테스트 시작")
        
        # 현재 도구 확인
        logger.debug(f"현재 도구: {self.current_tool}")
        logger.debug(f"현재 색상: {self.annotation_color}")
        logger.debug(f"현재 두께: {self.line_width}")
            
        # 피드백 항목 확인
        if self.feedback_items:
            current_item = self.feedback_items[self.current_index]
            logger.debug(f"현재 항목: {current_item['name']}")
            logger.debug(f"현재 주석 개수: {len(current_item.get('annotations', []))}")
        else:
            logger.debug("피드백 항목 없음")
        
        # 활성 캔버스 확인
        active_count = 0
        for canvas in self.active_canvases:
            try:
                if canvas.winfo_exists():
                    active_count += 1
            except:
                pass
        logger.debug(f"활성 캔버스 개수: {active_count}")
        
        logger.debug("✅ 주석 시스템 테스트 완료")
            
        # logger.debug("✅ 주석 시스템 테스트 완료")
    
    def schedule_update_check(self):
        """시작 시 업데이트 확인 스케줄링 (3초 후)"""
        if not self.update_checker:
            return
        
        def delayed_check():
            try:
                logger.info("시작 시 업데이트 확인 중...")
                self.check_for_updates_async(show_no_update=False)
            except Exception as e:
                logger.debug(f"시작 시 업데이트 확인 오류: {e}")
        
        # 3초 후 업데이트 확인 (UI 초기화 완료 후)
        self.root.after(3000, delayed_check)
    
    def manual_update_check(self):
        """수동 업데이트 확인 (버튼 클릭)"""
        if not self.update_checker:
            messagebox.showwarning('업데이트 확인', 'GitHub 업데이트 기능을 사용할 수 없습니다.')
            return
        
        logger.info("수동 업데이트 확인 시작")
        self.check_for_updates_async(show_no_update=True)
    
    def check_for_updates_async(self, show_no_update=True):
        """비동기 업데이트 확인"""
        if not self.update_checker:
            return
        
        try:
            # 진행률 다이얼로그 표시
            progress = AdvancedProgressDialog(
                self.root, 
                "업데이트 확인", 
                "GitHub에서 최신 버전을 확인하고 있습니다...",
                auto_close_ms=None,
                cancelable=False
            )
            
            def update_worker():
                """업데이트 확인 작업자"""
                try:
                    progress.update(30, "GitHub API 연결 중...")
                    update_info = self.update_checker.check_for_updates()
                    progress.update(100, "확인 완료!")
                    return update_info
                except Exception as e:
                    logger.error(f"업데이트 확인 작업 오류: {e}")
                    return {'error': f'업데이트 확인 실패: {str(e)}'}
            
            def on_update_complete(result):
                """업데이트 확인 완료 콜백"""
                progress.close()
                
                if 'error' in result:
                    logger.warning(f"업데이트 확인 실패: {result['error']}")
                    if show_no_update:
                        messagebox.showerror('업데이트 확인 실패', 
                                           f"업데이트 확인 중 오류가 발생했습니다:\n{result['error']}")
                    return
                
                if result.get('has_update', False):
                    logger.info(f"새 버전 발견: v{result['latest_version']}")
                    self.show_update_notification(result)
                else:
                    logger.info("최신 버전 사용 중")
                    if show_no_update:
                        messagebox.showinfo('업데이트 확인', 
                                          f"현재 최신 버전을 사용하고 있습니다.\n\n현재 버전: v{result['current_version']}")
            
            def on_update_error(error):
                """업데이트 확인 오류 콜백"""
                progress.close()
                logger.error(f"업데이트 확인 오류: {error}")
                if show_no_update:
                    messagebox.showerror('업데이트 확인 오류', 
                                       f'업데이트 확인 중 오류가 발생했습니다:\n{str(error)}')
            
            # 비동기 작업 실행
            self.task_manager.submit_task(
                update_worker,
                callback=on_update_complete,
                error_callback=on_update_error
            )
            
        except Exception as e:
            logger.error(f"업데이트 확인 시작 오류: {e}")
            if show_no_update:
                messagebox.showerror('오류', f'업데이트 확인을 시작할 수 없습니다: {str(e)}')
    
    def show_update_notification(self, update_info):
        """업데이트 알림 다이얼로그 표시"""
        try:
            dialog = UpdateNotificationDialog(self.root, update_info, self.update_checker)
            
            # 다이얼로그가 닫힐 때까지 대기
            self.root.wait_window(dialog.dialog)
            
            # 결과 처리
            if hasattr(dialog, 'result'):
                if dialog.result == 'downloaded':
                    self.update_status_message("업데이트 파일이 다운로드되었습니다")
                elif dialog.result == 'later':
                    self.update_status_message("업데이트를 나중에 진행합니다")
                    
        except Exception as e:
            logger.error(f"업데이트 알림 표시 오류: {e}")
            messagebox.showerror('오류', f'업데이트 알림을 표시할 수 없습니다: {str(e)}')

def setup_high_dpi():
    """고해상도 DPI 설정"""
    try:
        if sys.platform == 'win32':
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
                logger.info("✓ Windows DPI 인식 설정 완료")
            except Exception as e:
                logger.debug(f"DPI 설정 실패: {e}")
    except Exception as e:
        logger.debug(f"DPI 설정 오류: {e}")

def setup_encoding():
    """인코딩 설정"""
    try:
        import locale
        
        try:
            if sys.platform == 'win32':
                locale.setlocale(locale.LC_ALL, 'Korean_Korea.utf8')
            else:
                locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_ALL, '')
            except:
                pass
        
        logger.info("✓ 인코딩 설정 완료")
        
    except Exception as e:
        logger.debug(f"인코딩 설정 오류: {e}")

def check_dependencies():
    """의존성 모듈 확인"""
    missing_modules = []
    warnings = []
    
    if not PIL_AVAILABLE:
        missing_modules.append("Pillow")
    
    if not REPORTLAB_AVAILABLE:
        warnings.append("ReportLab (PDF 내보내기 불가)")
    if not PYAUTOGUI_AVAILABLE:
        warnings.append("PyAutoGUI (화면 캡처 불가)")
    if not PANDAS_AVAILABLE:
        warnings.append("pandas + openpyxl (Excel 내보내기 불가)")
    if not PSUTIL_AVAILABLE:
        warnings.append("psutil (메모리 모니터링 불가)")
    
    if missing_modules:
        error_msg = f"다음 필수 모듈이 없습니다: {', '.join(missing_modules)}\n\n"
        error_msg += "설치 방법:\n"
        error_msg += "1. 명령 프롬프트(CMD)를 관리자 권한으로 실행\n"
        for module in missing_modules:
            error_msg += f"2. pip install {module} 입력\n"
        error_msg += "3. 프로그램 재시작"
        return False, error_msg
    
    if warnings:
        warning_msg = f"다음 선택적 모듈이 없습니다: {', '.join(warnings)}\n\n"
        warning_msg += "모든 기능을 사용하려면 다음 명령으로 설치해주세요:\n"
        if not REPORTLAB_AVAILABLE:
            warning_msg += "pip install reportlab\n"
        if not PYAUTOGUI_AVAILABLE:
            warning_msg += "pip install pyautogui\n"
        if not PANDAS_AVAILABLE:
            warning_msg += "pip install pandas openpyxl\n"
        if not PSUTIL_AVAILABLE:
            warning_msg += "pip install psutil\n"
        logger.warning(warning_msg)
    
    return True, None

def main():
    """메인 함수 - 고화질 PDF + 완전 기능 최종 배포용 V1.9.3 (버그 수정)"""
    try:
        is_debug_mode = '--debug' in sys.argv or os.getenv('DEBUG_MODE') == '1'
        
        if is_debug_mode:
            logger.info("=" * 80)
            logger.info(f"피드백 캔버스 V{VERSION} - 배포 최적화 버전")
            logger.info(f"빌드일: {BUILD_DATE}")
            logger.info(f"시스템: {platform.system()} {platform.release()}")
            logger.info(f"Python: {sys.version}")
            logger.info("🔥 영역 드래그로 다중 주석 선택/이동/삭제")
            logger.info("🔥 PDF 텍스트 주석 완벽 출력 (배경/테두리 제거)")
            logger.info("🔥 빈 캔버스 생성 기능")
            logger.info("🔥 PDF 정보 입력창 분리")
            logger.info("🔥 UI 레이아웃 최적화")
            logger.info("🚀 배포 최적화: 동적 디버그, 로그 최적화, 콘솔 숨김")
            logger.info("=" * 80)
        else:
            logger.warning(f"피드백 캔버스 V{VERSION} 시작")
        
        deps_ok, error_msg = check_dependencies()
        if not deps_ok:
            messagebox.showerror("필수 모듈 오류", error_msg)
            sys.exit(1)
        
        setup_encoding()
        setup_high_dpi()
        
        root = tk.Tk()
        root.deiconify()  # 윈도우를 보이게 만듭니다
        
        try:
            root.tk.call('encoding', 'system', 'utf-8')
            root.option_add('*tearOff', False)
            logger.info("✓ tkinter 설정 완료")
        except Exception as e:
            logger.debug(f"tkinter 설정 오류: {e}")
        
        app = FeedbackCanvasTool(root)
        
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            error_msg = f"예상치 못한 오류가 발생했습니다:\n{exc_value}\n\n자세한 내용은 logs 폴더의 로그 파일을 확인해주세요."
            logger.error(f"전역 예외 발생: {exc_value}")
            logger.error(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
            
            try:
                messagebox.showerror("오류", error_msg)
            except:
                pass
        
        sys.excepthook = handle_exception
        
        if is_debug_mode:
            logger.info("✓ 애플리케이션 초기화 완료")
            logger.info("✅ 모든 기능이 정상적으로 로드되었습니다")
            logger.info("🚀 V1.9.3 배포 최적화 버전")
            logger.info("🎯 영역 선택으로 다중 주석 처리")
            logger.info("🎨 빈 캔버스 생성 기능")
            logger.info("📄 PDF 정보창 분리 및 완벽 출력")
            logger.info("🛡️ 프로덕션 모드 최적화 완료")
        else:
            logger.warning("애플리케이션 시작 완료")
        
        root.mainloop()
        
    except Exception as e:
        error_msg = f'프로그램 실행 중 치명적 오류 발생: {str(e)}'
        logger.critical(error_msg)
        logger.critical(traceback.format_exc())
        
        try:
            messagebox.showerror('치명적 오류', error_msg)
        except:
            # 프로덕션 모드에서는 무음 처리, 디버그 모드에서만 콘솔 출력
            if '--debug' in sys.argv or os.getenv('DEBUG_MODE') == '1':
                print(error_msg)
        
        sys.exit(1)
    
    finally:
        logger.info("프로그램 종료")

# 적응형 PDF 메서드 - 페이지 크기에 맞춤 최대 렌더링
def _adaptive_pdf_page_global(pdf_generator, canvas, item, index, page_width, page_height):
    """적응형 PDF 페이지 생성 - 완전 재설계 (고정 레이아웃)"""
    try:
        original_image = item['image']
        
        # 🔥 미리 계산된 레이아웃 정보 사용 (일관성 보장)
        layout = getattr(pdf_generator.app, 'adaptive_layout', {})
        if not layout:
            logger.error("❌ 레이아웃 정보가 없음 - 폴백 사용")
            pdf_generator._fallback_pdf_page(canvas, item, index, page_width, page_height)
            return
        
        # 레이아웃 정보 추출
        margin_points = layout.get('margin_points', 8)
        image_width_pt = layout.get('image_width_pt', 400)
        image_height_pt = layout.get('image_height_pt', 600)
        text_area_height = layout.get('text_area_height', 0)
        text_gap = layout.get('text_gap', 0)
        safe_gap = layout.get('safe_gap', max(text_gap * 2, 30))  # 안전한 간격 정보
        orientation = layout.get('orientation', '세로형')
        effective_dpi = layout.get('effective_dpi', 300)
        
        logger.info(f"🔥 고정 레이아웃 렌더링 시작 (페이지 {index+1}):")
        logger.info(f"   페이지: {page_width:.0f}x{page_height:.0f}pt")
        logger.info(f"   이미지: {image_width_pt:.0f}x{image_height_pt:.0f}pt ({effective_dpi}DPI)")
        logger.info(f"   텍스트: {text_area_height:.0f}pt (안전간격 {safe_gap}pt)")
        logger.info(f"   여백: {margin_points:.1f}pt, 타입: {orientation}")
        
        # 🔥 고정 레이아웃 위치 계산 (항상 일관됨, 겹침 완전 방지)
        # [상단여백] + [이미지] + [안전간격] + [텍스트영역] + [하단여백]
        
        # 이미지 위치 (페이지 중앙 정렬, 상단부터 시작)
        image_x = (page_width - image_width_pt) / 2  # 가로 중앙
        image_y = page_height - margin_points - image_height_pt  # 상단 여백부터
        
        # 💡 더 안전한 텍스트 위치 계산 (겹침 완전 방지)
        # 기본 안전 간격의 3배 + 최소 50pt 보장
        ultra_safe_gap = max(safe_gap * 3, 50)
        text_x = margin_points
        text_y = image_y - ultra_safe_gap  # 이미지에서 ultra_safe_gap만큼 아래 (완전 분리)
        
        # 텍스트 영역이 하단 여백보다 위에 있는지 검증
        text_bottom = text_y - text_area_height
        min_text_bottom = margin_points + 30  # 하단 최소 여백
        
        if text_bottom < min_text_bottom:
            # 텍스트 영역이 너무 아래로 내려가면 이미지를 위로 이동
            needed_space = min_text_bottom - text_bottom
            image_y = min(image_y + needed_space, page_height - margin_points - 50)  # 이미지를 위로 이동
            text_y = image_y - ultra_safe_gap  # 텍스트 위치 재계산
            logger.warning(f"⚠️ 겹침 방지: 이미지 위치 조정 {needed_space:.0f}pt 위로 이동")
        
        logger.info(f"🎯 고정 위치: 이미지({image_x:.0f}, {image_y:.0f}), 텍스트({text_x:.0f}, {text_y:.0f})")
        
        # 🔥 주석 분석 (디버깅 강화)
        annotations = item.get('annotations', [])
        logger.info(f"🎯 페이지 {index+1} 주석 분석: 총 {len(annotations)}개")
        if index == 0:
            logger.info(f"🔍 첫번째 페이지 특별 확인:")
            logger.info(f"  - item 키: {list(item.keys())}")
            if annotations:
                type_counts = {}
                for ann in annotations:
                    ann_type = ann.get('type', 'unknown')
                    type_counts[ann_type] = type_counts.get(ann_type, 0) + 1
                for ann_type, count in type_counts.items():
                    logger.info(f"    {ann_type}: {count}개")
            else:
                logger.error(f"❌ 첫번째 페이지에 주석이 없습니다!")
        
        # 투명도가 있는 이미지 주석 확인
        image_annotations = [ann for ann in annotations if ann.get('type') == 'image']
        has_transparent_images = any(
            ann.get('opacity', 100) < 100 
            for ann in image_annotations
        )
        
        logger.info(f"주석 분석: 전체 {len(annotations)}개, 이미지 {len(image_annotations)}개, 투명도: {has_transparent_images}")
        
        # 🔥 고정 크기 이미지 준비 (레이아웃에 맞는 정확한 크기)
        target_pixel_width = int((image_width_pt / 72) * effective_dpi)
        target_pixel_height = int((image_height_pt / 72) * effective_dpi)
        
        # 원본보다 크게 리샘플링하지 않음 (품질 저하 방지)
        if target_pixel_width > original_image.width or target_pixel_height > original_image.height:
            scaled_image = original_image  # 원본 사용
            logger.info("🔥 원본 해상도 사용 (확대 방지)")
        else:
            scaled_image = original_image.resize((target_pixel_width, target_pixel_height), 
                                               Image.Resampling.LANCZOS)
            logger.info(f"🔥 고품질 리샘플링: {target_pixel_width}x{target_pixel_height}px")
        
        # PDF 생성기에 안전한 속성 설정
        if not hasattr(pdf_generator, 'pdf_readability_mode'):
            pdf_generator.pdf_readability_mode = False
        
        # 🔥 고정 레이아웃 렌더링 방식 선택
        if orientation == "세로 긴 이미지(웹툰)":
            logger.info("고정 레이아웃 - 웹툰 모드: 해상도 우선 벡터 렌더링")
            
            # 웹툰은 투명도가 있어도 벡터 우선 (해상도 보존)
            if has_transparent_images:
                logger.info("웹툰 - 투명도 있지만 벡터 우선: 고해상도 유지")
                
            # 배경 이미지 렌더링 (고정 위치와 크기)
            img_buffer = io.BytesIO()
            if scaled_image.mode == 'RGBA':
                scaled_image.save(img_buffer, format='PNG', optimize=False, dpi=(int(effective_dpi), int(effective_dpi)))
            else:
                scaled_image.save(img_buffer, format='JPEG', quality=98, optimize=False, dpi=(int(effective_dpi), int(effective_dpi)))
            img_buffer.seek(0)
            
            canvas.drawImage(ImageReader(img_buffer), image_x, image_y, image_width_pt, image_height_pt)
            logger.info(f"🎯 웹툰 고해상도 렌더링: 위치({image_x:.0f}, {image_y:.0f}), 크기({image_width_pt:.0f}x{image_height_pt:.0f}pt)")
            
            # 벡터 주석 렌더링 (고정 위치 기준)
            pdf_generator.draw_vector_annotations_on_pdf(canvas, item, image_x, image_y, image_width_pt, image_height_pt)
                
        else:
            # 일반 이미지 처리
            if has_transparent_images or len(image_annotations) > 0:
                logger.info("고정 레이아웃 - 투명도/이미지주석 감지: 고품질 합성 방식 사용")
                # 투명도나 이미지 주석이 있으면 fallback 사용
                pdf_generator._fallback_pdf_page(canvas, item, index, page_width, page_height)
            else:
                logger.info("고정 레이아웃 - 벡터 모드 사용")
                
                # 벡터 모드 배경 이미지 렌더링 (고정 위치와 크기)
                img_buffer = io.BytesIO()
                if scaled_image.mode == 'RGBA':
                    scaled_image.save(img_buffer, format='PNG', optimize=False, dpi=(int(effective_dpi), int(effective_dpi)))
                else:
                    scaled_image.save(img_buffer, format='JPEG', quality=98, optimize=False, dpi=(int(effective_dpi), int(effective_dpi)))
                img_buffer.seek(0)
                
                canvas.drawImage(ImageReader(img_buffer), image_x, image_y, image_width_pt, image_height_pt)
                logger.info(f"🎯 고정 레이아웃 배경 이미지: 위치({image_x:.0f}, {image_y:.0f}), 크기({image_width_pt:.0f}x{image_height_pt:.0f}pt)")
                
                # 벡터 주석 렌더링 (고정 위치 기준)
                pdf_generator.draw_vector_annotations_on_pdf(canvas, item, image_x, image_y, image_width_pt, image_height_pt)
        
        logger.info(f"✅ 고정 레이아웃 이미지 렌더링 완료")
        
        # 🔥 고정 레이아웃 피드백 텍스트 렌더링
        if text_area_height > 0:
            feedback_text = item.get('feedback_text', '').strip()
            if feedback_text:
                logger.info(f"📝 고정 레이아웃 텍스트 렌더링: {len(feedback_text)}자, 위치({text_x:.0f}, {text_y:.0f})")
                
                # 고정 위치에 텍스트 렌더링 (위치는 이미 계산됨)
                _add_adaptive_feedback_text_natural(pdf_generator, canvas, item, index, text_y, text_area_height, page_width, margin_points, orientation)
                logger.info(f"📝 고정 레이아웃 텍스트 완료: 위치={text_y:.0f}, 높이={text_area_height:.0f}pt")
            else:
                logger.info("📝 피드백 텍스트 없음")
        
        # 🔥 페이지 번호
        skip_title = getattr(pdf_generator.app, 'skip_title_page', False) if pdf_generator.app else False
        page_number = index + 1 if skip_title else index + 2
        
        canvas.setFont('Helvetica', 9)
        canvas.drawString(page_width - 80, 15, f"{page_number}")
        
        logger.info(f"🎯 고정 레이아웃 PDF 페이지 생성 완료: 페이지 {page_number}")
        
    except Exception as e:
        logger.error(f"적응형 PDF 페이지 생성 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # 오류 발생 시 폴백 메서드 사용
        pdf_generator._fallback_pdf_page(canvas, item, index, page_width, page_height)

def _render_vector_annotation_adaptive(pdf_generator, canvas, annotation, base_x, base_y, scale_x, scale_y, original_image):
    """적응형 PDF에서 벡터 주석 렌더링 (고화질) - 완전 구현"""
    try:
        ann_type = annotation.get('type', '')
        points = annotation.get('points', [])
        color = annotation.get('color', '#FF0000')
        width = annotation.get('width', 2)
        
        logger.debug(f"🎯 주석 렌더링: type={ann_type}, points={len(points)}개, color={color}, width={width}")
        
        if not points and ann_type != 'image':
            logger.debug(f"⚠️ 주석 건너뜀: {ann_type} - 포인트 없음")
            return
        
        # 이미지 높이 정보
        image_height = original_image.height
        
        # 색상 변환
        if color.startswith('#'):
            color = color[1:]
        try:
            r = int(color[0:2], 16) / 255.0
            g = int(color[2:4], 16) / 255.0
            b = int(color[4:6], 16) / 255.0
        except:
            r, g, b = 1.0, 0.0, 0.0  # 기본값: 빨간색
        
        # 선 굵기 스케일링 (고화질)
        scaled_width = max(width * min(scale_x, scale_y), 0.5)
        canvas.setStrokeColorRGB(r, g, b)
        canvas.setLineWidth(scaled_width)
        
        # 좌표 변환 함수
        def transform_point(point):
            x, y = point
            # 이미지 좌표계 → PDF 좌표계 변환 (Y축 뒤집기)
            pdf_x = base_x + (x * scale_x)
            pdf_y = base_y + ((image_height - y) * scale_y)
            return pdf_x, pdf_y
        
        if ann_type == 'arrow':
            # 🔥 A4 고정과 호환되는 화살표 좌표 처리
            if 'start_x' in annotation and 'start_y' in annotation:
                # A4 고정 방식: start_x, start_y, end_x, end_y
                start_point = (annotation['start_x'], annotation['start_y'])
                end_point = (annotation['end_x'], annotation['end_y'])
                start_x, start_y = transform_point(start_point)
                end_x, end_y = transform_point(end_point)
                logger.debug(f"🎯 A4 호환 화살표 좌표: ({annotation['start_x']}, {annotation['start_y']}) → ({annotation['end_x']}, {annotation['end_y']})")
            elif len(points) >= 2:
                # 새로운 방식: points 배열
                start_x, start_y = transform_point(points[0])
                end_x, end_y = transform_point(points[-1])
                logger.debug(f"🎯 점 배열 화살표 좌표: {points[0]} → {points[-1]}")
            else:
                logger.warning(f"⚠️ 화살표 좌표 데이터 없음: {annotation}")
                return
            
            # 화살표 본체
            canvas.line(start_x, start_y, end_x, end_y)
            
            # 화살표 머리 (고화질)
            import math
            angle = math.atan2(end_y - start_y, end_x - start_x)
            arrow_size = max(scaled_width * 4, 8)
            
            # 화살표 끝점
            arrow_x1 = end_x - arrow_size * math.cos(angle - 0.5)
            arrow_y1 = end_y - arrow_size * math.sin(angle - 0.5)
            arrow_x2 = end_x - arrow_size * math.cos(angle + 0.5)
            arrow_y2 = end_y - arrow_size * math.sin(angle + 0.5)
            
            canvas.line(end_x, end_y, arrow_x1, arrow_y1)
            canvas.line(end_x, end_y, arrow_x2, arrow_y2)
            logger.debug(f"🎯 벡터 화살표 렌더링: ({start_x:.0f},{start_y:.0f}) → ({end_x:.0f},{end_y:.0f}), 두께={scaled_width:.1f}")
        
        elif ann_type == 'line':
            # 🔥 A4 고정과 호환되는 라인 좌표 처리
            if 'start_x' in annotation and 'start_y' in annotation:
                # A4 고정 방식: start_x, start_y, end_x, end_y
                start_point = (annotation['start_x'], annotation['start_y'])
                end_point = (annotation['end_x'], annotation['end_y'])
                start_x, start_y = transform_point(start_point)
                end_x, end_y = transform_point(end_point)
                logger.debug(f"🎯 A4 호환 라인 좌표: ({annotation['start_x']}, {annotation['start_y']}) → ({annotation['end_x']}, {annotation['end_y']})")
            elif len(points) >= 2:
                # 새로운 방식: points 배열
                start_x, start_y = transform_point(points[0])
                end_x, end_y = transform_point(points[-1])
                logger.debug(f"🎯 점 배열 라인 좌표: {points[0]} → {points[-1]}")
            else:
                logger.warning(f"⚠️ 라인 좌표 데이터 없음: {annotation}")
                return
            
            canvas.line(start_x, start_y, end_x, end_y)
            logger.debug(f"🎯 벡터 라인 렌더링: ({start_x:.0f},{start_y:.0f}) → ({end_x:.0f},{end_y:.0f}), 두께={scaled_width:.1f}")
        
        elif ann_type == 'pen':
            # 🔥 벡터 펜 스트로크
            if len(points) >= 2:
                path = canvas.beginPath()
                start_x, start_y = transform_point(points[0])
                path.moveTo(start_x, start_y)
                
                for point in points[1:]:
                    x, y = transform_point(point)
                    path.lineTo(x, y)
                
                canvas.drawPath(path, stroke=1, fill=0)
                logger.debug(f"🎯 벡터 펜 렌더링: {len(points)}점, 두께={scaled_width:.1f}")
        
        elif ann_type in ['rectangle', 'circle', 'rect', 'oval']:
            # 🔥 A4 고정과 호환되는 도형 좌표 처리
            if 'x1' in annotation and 'y1' in annotation:
                # A4 고정 방식: x1, y1, x2, y2
                point1 = (annotation['x1'], annotation['y1'])
                point2 = (annotation['x2'], annotation['y2'])
                x1, y1 = transform_point(point1)
                x2, y2 = transform_point(point2)
                logger.debug(f"🎯 A4 호환 도형 좌표: ({annotation['x1']}, {annotation['y1']}) → ({annotation['x2']}, {annotation['y2']})")
            elif len(points) >= 2:
                # 새로운 방식: points 배열
                x1, y1 = transform_point(points[0])
                x2, y2 = transform_point(points[1])
                logger.debug(f"🎯 점 배열 도형 좌표: {points[0]} → {points[1]}")
            else:
                logger.warning(f"⚠️ 도형 좌표 데이터 없음: {annotation}")
                return
            
            min_x, max_x = min(x1, x2), max(x1, x2)
            min_y, max_y = min(y1, y2), max(y1, y2)
            
            if ann_type in ['rectangle', 'rect']:
                canvas.rect(min_x, min_y, max_x - min_x, max_y - min_y, stroke=1, fill=0)
                logger.debug(f"🎯 벡터 사각형 렌더링: ({min_x:.0f},{min_y:.0f}), 크기=({max_x-min_x:.0f}x{max_y-min_y:.0f})")
            else:  # circle, oval
                center_x = (min_x + max_x) / 2
                center_y = (min_y + max_y) / 2
                width = abs(max_x - min_x)
                height = abs(max_y - min_y)
                
                # A4 고정과 동일한 타원 처리
                canvas.ellipse(center_x - width/2, center_y - height/2,
                             center_x + width/2, center_y + height/2,
                             stroke=1, fill=0)
                logger.debug(f"🎯 벡터 타원 렌더링: 중심=({center_x:.0f},{center_y:.0f}), 크기=({width:.0f}x{height:.0f})")
        
        elif ann_type == 'text':
            # 🔥 A4 고정과 호환되는 텍스트 좌표 처리
            if 'x' in annotation and 'y' in annotation:
                # A4 고정 방식: x, y
                text_point = (annotation['x'], annotation['y'])
                x, y = transform_point(text_point)
                logger.debug(f"🎯 A4 호환 텍스트 좌표: ({annotation['x']}, {annotation['y']})")
            elif points and len(points) > 0:
                # 새로운 방식: points 배열
                x, y = transform_point(points[0])
                logger.debug(f"🎯 점 배열 텍스트 좌표: {points[0]}")
            else:
                logger.warning(f"⚠️ 텍스트 좌표 데이터 없음: {annotation}")
                return
            
            text_content = annotation.get('text', '')
            if not text_content:
                logger.warning(f"⚠️ 텍스트 내용 없음")
                return
                
            # 🔥 A4 고정과 동일한 폰트 크기 처리
            base_font_size = annotation.get('font_size', 12)
            font_size = max(base_font_size, 10)  # A4 고정과 동일한 최소 크기
            
            canvas.setFillColorRGB(r, g, b)
            try:
                korean_font = pdf_generator.font_manager.register_pdf_font()
                canvas.setFont(korean_font, font_size)
            except:
                canvas.setFont('Helvetica', font_size)
            
            # A4 고정과 동일한 텍스트 위치 보정
            canvas.drawString(x, y - font_size, text_content)
            logger.debug(f"🎯 벡터 텍스트 렌더링: '{text_content[:20]}...', 위치=({x:.0f},{y:.0f}), 크기={font_size:.1f}")
        
        elif ann_type == 'image':
            # 🔥 주석 이미지 (견본 캡처, 투명도 이미지 포함)
            image_data = annotation.get('image_data')
            if image_data:
                try:
                    # Base64 이미지 데이터 디코딩
                    import base64
                    decoded_data = base64.b64decode(image_data)
                    ann_image = Image.open(io.BytesIO(decoded_data))
                    
                    # 주석 이미지 위치 및 크기 정보
                    ann_x = annotation.get('x', 0)
                    ann_y = annotation.get('y', 0)
                    ann_width = annotation.get('width', ann_image.width)
                    ann_height = annotation.get('height', ann_image.height)
                    
                    # 이미지 좌표계에서 PDF 좌표계로 변환
                    pdf_x = base_x + (ann_x * scale_x)
                    pdf_y = base_y + ((image_height - ann_y - ann_height) * scale_y)
                    pdf_width = ann_width * scale_x
                    pdf_height = ann_height * scale_y
                    
                    # 🔥 회전 처리
                    rotation = annotation.get('rotation', 0)
                    if rotation != 0:
                        # 회전된 이미지 생성
                        ann_image = ann_image.rotate(-rotation, expand=True, fillcolor=(255, 255, 255, 0))
                    
                    # 🔥 반전 처리
                    if annotation.get('flip_horizontal', False):
                        ann_image = ann_image.transpose(Image.FLIP_LEFT_RIGHT)
                    if annotation.get('flip_vertical', False):
                        ann_image = ann_image.transpose(Image.FLIP_TOP_BOTTOM)
                    
                    # 🔥 A4 고정과 동일한 투명도 처리 (완전 개선)
                    opacity = annotation.get('opacity', 100) / 100.0
                    logger.debug(f"🎨 주석 이미지 투명도: {opacity:.2f} ({annotation.get('opacity', 100)}%)")
                    
                    # 🔥 A4 고정과 동일한 투명도 처리 방식 적용
                    if opacity < 1.0 and ann_image.mode == 'RGBA':
                        alpha = ann_image.split()[-1]
                        alpha = alpha.point(lambda p: int(p * opacity))
                        ann_image.putalpha(alpha)
                        logger.debug(f"🎨 A4 고정 방식 투명도 적용: {opacity:.2f}")
                    
                    # 이미지 버퍼 준비
                    img_buffer = io.BytesIO()
                    
                    # 🔥 A4 고정과 동일한 저장 방식 (RGB 변환 + 알파 블렌딩)
                    if ann_image.mode == 'RGBA':
                        # 투명한 배경을 흰색으로 변환 (고품질 알파 블렌딩)
                        rgb_img = Image.new('RGB', ann_image.size, (255, 255, 255))
                        if opacity < 1.0:
                            # 투명도가 있는 경우 고품질 알파 블렌딩
                            rgb_img.paste(ann_image, mask=ann_image.split()[-1])
                        else:
                            rgb_img.paste(ann_image, mask=ann_image.split()[-1])
                        ann_image = rgb_img
                        logger.debug("🎨 A4 고정 방식 RGBA → RGB 변환 완료")
                    elif ann_image.mode != 'RGB':
                        ann_image = ann_image.convert('RGB')
                        logger.debug(f"🎨 {ann_image.mode} → RGB 변환")
                    
                    # 🔥 최고 품질로 저장 (A4 고정과 동일)
                    ann_image.save(img_buffer, format='PNG', 
                                  optimize=False, compress_level=0)
                    logger.debug(f"🎨 투명도 이미지 고품질 PNG 저장 완료: opacity={opacity:.2f}")
                    
                    img_buffer.seek(0)
                    
                    # 🔥 흰색 아웃라인 처리 (UI 다이얼로그와 동일한 방식)
                    if annotation.get('outline', False):
                        outline_width = annotation.get('outline_width', 3) * min(scale_x, scale_y)
                        # 흰색 아웃라인 설정 (UI와 일치)
                        canvas.setStrokeColorRGB(1.0, 1.0, 1.0)  # 순백색 아웃라인
                        canvas.setLineWidth(outline_width)
                        
                        # 더 두꺼운 흰색 테두리 효과 (UI ImageDraw 방식과 유사)
                        for offset in range(int(outline_width), 0, -1):
                            canvas.rect(pdf_x - offset, pdf_y - offset, 
                                      pdf_width + (offset * 2), pdf_height + (offset * 2), 
                                      stroke=1, fill=0)
                        
                        logger.debug(f"🎨 흰색 아웃라인 PDF 렌더링: 너비={outline_width:.1f}pt")
                    
                    # PDF에 이미지 추가
                    canvas.drawImage(ImageReader(img_buffer), pdf_x, pdf_y, pdf_width, pdf_height)
                    logger.debug(f"🎨 주석 이미지 렌더링 완료: 위치({pdf_x:.0f}, {pdf_y:.0f}), 크기({pdf_width:.0f}x{pdf_height:.0f}), 투명도={opacity:.2f}, 회전={rotation}°")
                    
                except Exception as img_e:
                    logger.error(f"주석 이미지 렌더링 오류: {img_e}")
                    # 이미지 로드 실패 시 대체 표시
                    try:
                        ann_x = annotation.get('x', 0)
                        ann_y = annotation.get('y', 0)
                        pdf_x = base_x + (ann_x * scale_x)
                        pdf_y = base_y + ((image_height - ann_y - 20) * scale_y)
                        
                        canvas.setStrokeColorRGB(1.0, 0.0, 0.0)
                        canvas.setFillColorRGB(1.0, 0.0, 0.0)
                        canvas.rect(pdf_x, pdf_y, 80, 20, stroke=1, fill=0)
                        canvas.setFont('Helvetica', 8)
                        canvas.drawString(pdf_x + 5, pdf_y + 10, "Image Error")
                    except:
                        pass
        
        logger.debug(f"🎨 벡터 주석 렌더링: {ann_type}, 크기={scaled_width:.1f}")
        
    except Exception as e:
        logger.error(f"벡터 주석 렌더링 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())


def _add_adaptive_feedback_text_natural(pdf_generator, canvas, item, index, text_y, text_area_height, page_width, margin, orientation='일반'):
    """적응형 PDF에 피드백 텍스트 추가 - 고정 레이아웃 (글로벌 함수)"""
    try:
        feedback_text = item.get('feedback_text', '').strip()
        if not feedback_text:
            return
        
        korean_font = pdf_generator.font_manager.register_pdf_font()
        
        # 🔥 타입별 텍스트 박스 여백 조정 (매개변수로 받은 orientation 사용)
        adaptive_orientation = orientation
        
        if adaptive_orientation == "세로 긴 이미지(웹툰)":
            # 웹툰용 극소 텍스트 박스 여백 - 더욱 축소
            text_box_margin = max(1, margin * 0.2)  # 최소 1pt, 일반 여백의 20%
            logger.info(f"📝 웹툰 텍스트 박스 여백 극소화: {text_box_margin:.1f}pt (약 {text_box_margin*25.4/72:.1f}mm)")
        else:
            # 일반 이미지는 원래 여백 사용
            text_box_margin = margin
        
        # 🔥 배경 박스 렌더링 (여백 최적화 적용)
        canvas.setStrokeColorRGB(0.8, 0.8, 0.8)
        canvas.setFillColorRGB(0.98, 0.98, 0.98)
        canvas.rect(text_box_margin, text_y - text_area_height, 
                   page_width - (text_box_margin * 2), text_area_height, 
                   stroke=1, fill=1)
        
        # 🔥 A4 고정과 동일한 제목
        canvas.setFillColorRGB(0.2, 0.2, 0.2)
        canvas.setFont(korean_font, 14)
        
        title_parts = []
        if pdf_generator.app and hasattr(pdf_generator.app, 'show_index_numbers') and pdf_generator.app.show_index_numbers.get():
            title_parts.append(f"#{index + 1}")
        
        if pdf_generator.app and hasattr(pdf_generator.app, 'show_name') and pdf_generator.app.show_name.get():
            title_parts.append(item.get('name', f'피드백 #{index + 1}'))
        
        if pdf_generator.app and hasattr(pdf_generator.app, 'show_timestamp') and pdf_generator.app.show_timestamp.get():
            title_parts.append(f"({item.get('timestamp', '')})")
        
        title_text = " ".join(title_parts) if title_parts else f"피드백 #{index + 1}"
        
        # 🔥 웹툰 최적화된 텍스트 영역 설정 (제목 위치 먼저 계산)
        if adaptive_orientation == "세로 긴 이미지(웹툰)":
            # 웹툰용 텍스트 너비 최적화 (여백 극소화)
            max_text_width = page_width - (text_box_margin * 2) - 8  # 내부 여백 극소화 (15→8)
            title_offset = text_box_margin + 3  # 제목 여백 극소화 (5→3)
            logger.debug(f"📝 웹툰 텍스트 너비 극소화: {max_text_width:.0f}pt, 제목오프셋: {title_offset:.0f}pt")
        else:
            # 일반 이미지는 A4 고정과 동일
            max_text_width = page_width - (text_box_margin * 2) - 20
            title_offset = text_box_margin + 10
        
        title_y = text_y - 25
        canvas.drawString(title_offset, title_y, f"💬 {title_text}")
        
        # 텍스트 색상 설정
        canvas.setFillColorRGB(0.1, 0.1, 0.1)
        
        # 스마트 폰트 크기 자동 조정 (A4 고정과 동일)
        available_height = text_area_height - 45  # 하단 여백 축소
        
        # 피드백 텍스트 폰트 크기 증가 - A4 고정과 동일
        text_length = len(feedback_text)
        if text_length < 100:
            initial_font_size = 16  # 짧은 텍스트
        elif text_length < 300:
            initial_font_size = 15  # 중간 텍스트
        elif text_length < 600:
            initial_font_size = 14  # 긴 텍스트
        else:
            initial_font_size = 13  # 매우 긴 텍스트
        
        # 🔥 최적 폰트 크기 찾기 (텍스트가 잘리지 않도록 개선)
        best_font_size = initial_font_size
        best_line_height = 18  # 줄 간격
        
        # 더 작은 폰트 크기까지 시도 (7pt까지)
        for font_size in range(initial_font_size, 6, -1):  # 최소 7까지 (10 → 7)
            canvas.setFont(korean_font, font_size)
            text_lines = pdf_generator._wrap_text_for_pdf(feedback_text, max_text_width, korean_font, font_size, canvas)
            line_height = font_size + 4  # 줄 간격 최적화 (5 → 4)
            total_height = len(text_lines) * line_height
            
            if total_height <= available_height:
                best_font_size = font_size
                best_line_height = line_height
                break
        
        # 🔥 여전히 맞지 않으면 최소 폰트로 강제 설정
        if best_font_size == initial_font_size:
            canvas.setFont(korean_font, 7)
            text_lines = pdf_generator._wrap_text_for_pdf(feedback_text, max_text_width, korean_font, 7, canvas)
            total_height = len(text_lines) * 11
            if total_height > available_height:
                # 매우 긴 텍스트: 줄 간격을 더욱 줄임
                best_font_size = 7
                best_line_height = 9  # 최소 줄 간격
                logger.warning(f"매우 긴 텍스트 감지: 최소 폰트(7pt) 및 줄간격(9pt) 적용")
            else:
                best_font_size = 7
                best_line_height = 11
        
        # 최종 텍스트 렌더링 (잘리지 않도록 모든 텍스트 출력)
        canvas.setFont(korean_font, best_font_size)
        text_lines = pdf_generator._wrap_text_for_pdf(feedback_text, max_text_width, korean_font, best_font_size, canvas)
        
        content_y = title_y - 30
        
        # 웹툰에서는 텍스트 내부 여백도 축소 (미리 계산)
        inner_text_margin = 8 if adaptive_orientation == "세로 긴 이미지(웹툰)" else 15
        
        # 🔥 텍스트 영역이 동적으로 계산되었으므로 모든 텍스트 출력
        for i, line in enumerate(text_lines):
            # 하단 여백 체크만 유지 (max_lines 제한 제거)
            if content_y < text_y - text_area_height + 2:  
                # 마지막 라인에서 텍스트가 잘릴 경우에만 "... (더보기)" 표시
                if i < len(text_lines) - 1:
                    canvas.setFont(korean_font, max(7, best_font_size - 1))
                    canvas.setFillColorRGB(0.5, 0.5, 0.5)
                    canvas.drawString(text_box_margin + inner_text_margin, content_y + best_line_height, "... (내용이 더 있습니다)")
                break
            canvas.drawString(text_box_margin + inner_text_margin, content_y, line)
            content_y -= best_line_height
        
        logger.debug(f"적응형 스마트 폰트 적용: {best_font_size}pt, {len(text_lines)}줄, 여백최적화: {adaptive_orientation}")
        
    except Exception as e:
        logger.error(f"A4 동일 레이아웃 피드백 텍스트 추가 오류: {e}")


def _add_adaptive_feedback_text_global(pdf_generator, canvas, item, index, text_y, text_area_height, page_width, margin):
    """적응형 PDF에 피드백 텍스트 추가 (글로벌 함수) - 호환성 유지"""
    # 🔥 text_y는 이미 올바르게 계산되어 전달됨 (이미지 아래 위치)
    _add_adaptive_feedback_text_natural(pdf_generator, canvas, item, index, text_y, text_area_height, page_width, margin)

# PDF 생성기 클래스에 적응형 메서드 동적 추가
def add_adaptive_methods_to_pdf_generator():
    """PDF 생성기 클래스에 적응형 메서드를 동적으로 추가"""
    try:
        # 🔥 글로벌 스코프에서 HighQualityPDFGenerator 클래스 찾기
        pdf_gen_class = None
        for name, obj in globals().items():
            if isinstance(obj, type) and name == 'HighQualityPDFGenerator':
                pdf_gen_class = obj
                break
        
        if pdf_gen_class is None:
            logger.error("HighQualityPDFGenerator 클래스를 찾을 수 없습니다")
            return
        
        # 🔥 적응형 메서드를 클래스에 동적으로 추가
        def _adaptive_pdf_page(self, canvas, item, index, page_width, page_height):
            return _adaptive_pdf_page_global(self, canvas, item, index, page_width, page_height)
        
        def _add_adaptive_feedback_text(self, canvas, item, index, text_y, text_area_height, page_width, margin):
            return _add_adaptive_feedback_text_global(self, canvas, item, index, text_y, text_area_height, page_width, margin)
        
        def _add_adaptive_feedback_text_natural(self, canvas, item, index, text_y, text_area_height, page_width, margin):
            return _add_adaptive_feedback_text_natural(self, canvas, item, index, text_y, text_area_height, page_width, margin)
        
        def _render_vector_annotation_adaptive(self, canvas, annotation, base_x, base_y, scale_x, scale_y, original_image):
            return _render_vector_annotation_adaptive(self, canvas, annotation, base_x, base_y, scale_x, scale_y, original_image)
        
        # 클래스에 메서드 추가
        setattr(pdf_gen_class, '_adaptive_pdf_page', _adaptive_pdf_page)
        setattr(pdf_gen_class, '_add_adaptive_feedback_text', _add_adaptive_feedback_text)
        setattr(pdf_gen_class, '_add_adaptive_feedback_text_natural', _add_adaptive_feedback_text_natural)
        setattr(pdf_gen_class, '_render_vector_annotation_adaptive', _render_vector_annotation_adaptive)
        
        logger.info(f"✅ HighQualityPDFGenerator 클래스에 적응형 PDF 메서드 4개 추가 완료")
        
    except Exception as e:
        logger.error(f"적응형 메서드 동적 추가 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    # 프로덕션 모드에서는 콘솔 창 숨김
    if os.name == 'nt' and not ('--debug' in sys.argv or os.getenv('DEBUG_MODE') == '1'):
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except:
            pass
    
    # 적응형 메서드 동적 추가
    add_adaptive_methods_to_pdf_generator()
    
    main()
    
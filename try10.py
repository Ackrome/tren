import sys
import re
import asyncio
import threading
import socket
import os
import json
import uuid
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout,
    QWidget, QHBoxLayout, QFileDialog, QMessageBox, QInputDialog,
    QScrollArea, QFrame, QLabel, QSplitter
)
from PyQt5.QtCore import QObject, pyqtSignal, QThread, Qt
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor

try:
    import websockets
except ImportError:
    print("Error: The 'websockets' library is required. Please install it with 'pip install websockets'")
    sys.exit(1)

try:
    from pyngrok import ngrok
except ImportError:
    print("Error: The 'pyngrok' library is required. Please install it with 'pip install pyngrok'")
    sys.exit(1)

try:
    import nbformat
except ImportError:
    print("Error: The 'nbformat' library is required. Please install it with 'pip install nbformat'")
    sys.exit(1)

try:
    from jupyter_client import KernelManager
except ImportError:
    print("Error: The 'jupyter_client' library is required. Please install it with 'pip install jupyter_client'")
    sys.exit(1)


# --- 1. Syntax Highlighting (No Changes) ---
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.highlighting_rules = []
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#c586c0"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            '\\bdef\\b', '\\bclass\\b', '\\bif\\b', '\\belif\\b', '\\belse\\b',
            '\\bfor\\b', '\\bwhile\\b', '\\btry\\b', '\\bexcept\\b', '\\bfinally\\b',
            '\\breturn\\b', '\\byield\\b', '\\bimport\\b', '\\bfrom\\b', '\\bas\\b',
            '\\bpass\\b', '\\bcontinue\\b', '\\bbreak\\b', '\\bin\\b', '\\bis\\b',
            '\\band\\b', '\\bor\\b', '\\bnot\\b', '\\blambda\\b', '\\bwith\\b',
            '\\bself\\b', '\\bTrue\\b', '\\bFalse\\b', '\\bNone\\b'
        ]
        self.highlighting_rules.extend([(re.compile(pattern), keyword_format) for pattern in keywords])
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        self.highlighting_rules.append((re.compile("#[^\n]*"), comment_format))
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))
        self.highlighting_rules.append((re.compile("\".*\""), string_format))
        self.highlighting_rules.append((re.compile("'.*'"), string_format))
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#b5cea8"))
        self.highlighting_rules.append((re.compile("\\b[0-9]+\\.?[0-9]*\\b"), number_format))
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#dcdcaa"))
        self.highlighting_rules.append((re.compile("\\b\\w+\\s*(?=\\()"), function_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), format)


# --- 2. Code Editor Widget (Modified for Auto-Resizing) ---
class CodeEditor(QTextEdit):
    def __init__(self, cell_widget, parent=None):
        super().__init__(parent)
        self.cell_widget = cell_widget
        self.highlighter = PythonHighlighter(self.document())
        self.ignore_next_text_change = False
        self.setFont(QFont("Courier", 12))
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        self.textChanged.connect(self.on_text_changed)
        self.textChanged.connect(self.update_height)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def set_text_from_websocket(self, text):
        self.ignore_next_text_change = True
        self.setPlainText(text)
        self.ignore_next_text_change = False

    def on_text_changed(self):
        if not self.ignore_next_text_change:
            self.cell_widget.main_window.on_cell_text_changed(self.cell_widget)

    def update_height(self):
        doc_height = self.document().size().height()
        margins = self.contentsMargins()
        total_height = int(doc_height + margins.top() + margins.bottom())
        self.setFixedHeight(total_height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_height()


# --- 3. Websocket Networking (No Changes) ---
class WebsocketThread(QThread):
    message_received = pyqtSignal(str)
    connection_status_changed = pyqtSignal(str)

    def __init__(self, uri="", main_window=None):
        super().__init__()
        self.uri = uri
        self.is_server = not bool(uri)
        self.main_window = main_window
        self.loop = None
        self.clients = set()
        self.shutdown_event = None

    async def server_logic(self, websocket, path=None):
        if self.main_window:
            initial_state = self.main_window.get_notebook_state()
            initial_message = json.dumps({
                'action': 'initial_state',
                'notebook': initial_state
            })
            await websocket.send(initial_message)
            
        self.clients.add(websocket)
        self.connection_status_changed.emit(f"Connected Clients: {len(self.clients)}")
        
        try:
            async for message in websocket:
                self.message_received.emit(message)
                for client in self.clients:
                    if client != websocket:
                        await client.send(message)
        finally:
            self.clients.remove(websocket)
            self.connection_status_changed.emit(f"Connected Clients: {len(self.clients)}")

    async def client_consumer(self, websocket):
        try:
            async for message in websocket:
                self.message_received.emit(message)
        except websockets.exceptions.ConnectionClosed:
            pass

    async def main_async_logic(self):
        if self.is_server:
            server = await websockets.serve(self.server_logic, '0.0.0.0', 8765)
            await self.shutdown_event.wait()
            server.close()
            await server.wait_closed()
        else:
            try:
                async with websockets.connect(self.uri) as websocket:
                    self.connection_status_changed.emit(f"Connected to {self.uri}")
                    self.websocket_connection = websocket
                    consumer_task = asyncio.create_task(self.client_consumer(websocket))
                    await self.shutdown_event.wait()
                    consumer_task.cancel()
            except Exception as e:
                self.connection_status_changed.emit(f"Error: {e}")

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.shutdown_event = asyncio.Event()
        self.loop.run_until_complete(self.main_async_logic())
        self.loop.close()

    async def _broadcast(self, message):
        if self.clients:
            tasks = [client.send(message) for client in self.clients]
            await asyncio.gather(*tasks)

    def send_message(self, message):
        if self.loop and self.loop.is_running():
            if self.is_server:
                asyncio.run_coroutine_threadsafe(self._broadcast(message), self.loop)
            elif hasattr(self, 'websocket_connection'):
                asyncio.run_coroutine_threadsafe(self.websocket_connection.send(message), self.loop)

    def stop(self):
        if self.loop and self.shutdown_event and not self.shutdown_event.is_set():
            self.loop.call_soon_threadsafe(self.shutdown_event.set)
        self.wait()


# --- 4. Cell Widget (Modified for Resizeable Output) ---
class CellWidget(QFrame):
    def __init__(self, main_window, cell_id, cell_type='code', content=''):
        super().__init__()
        self.main_window = main_window
        self.cell_id = cell_id
        self.cell_type = cell_type

        self.setFrameShape(QFrame.StyledPanel)
        self.layout = QVBoxLayout(self)

        self.splitter = QSplitter(Qt.Vertical)
        self.layout.addWidget(self.splitter)

        self.input_area = CodeEditor(self)
        self.input_area.setPlainText(content)
        self.splitter.addWidget(self.input_area)

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setFont(QFont("Courier", 11))
        self.output_area.setStyleSheet("background-color: #2a2a2a; color: #d4d4d4;")
        self.output_area.setVisible(False)
        self.splitter.addWidget(self.output_area)
        self.splitter.setSizes([100, 100])

        button_layout = QHBoxLayout()
        self.run_button = QPushButton("Run")
        self.add_button = QPushButton("Add Cell")
        self.delete_button = QPushButton("Delete Cell")

        buttons = [self.run_button, self.add_button, self.delete_button]
        for btn in buttons:
            button_layout.addWidget(btn)
        self.layout.addLayout(button_layout)
        
        self.run_button.clicked.connect(self.run_code)
        self.add_button.clicked.connect(self.add_cell)
        self.delete_button.clicked.connect(self.delete_cell)

    def run_code(self):
        self.main_window.run_code_in_cell(self)
        
    def add_cell(self):
        self.main_window.add_new_cell(self)

    def delete_cell(self):
        self.main_window.delete_cell(self)


# --- 5. Main Application Window (Modified for Scrolling) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Collaborative IPYNB Editor")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        
        self.notebook = []
        self.cell_widgets = {}

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.notebook_widget = QWidget()
        self.notebook_layout = QVBoxLayout(self.notebook_widget)
        self.notebook_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.notebook_widget)
        self.main_layout.addWidget(self.scroll_area)

        top_button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.load_button = QPushButton("Load")
        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        buttons = [self.save_button, self.load_button, self.connect_button, self.disconnect_button]
        for btn in buttons:
            top_button_layout.addWidget(btn)
        self.main_layout.addLayout(top_button_layout)

        self.save_button.clicked.connect(self.save_notebook)
        self.load_button.clicked.connect(self.load_notebook)
        self.connect_button.clicked.connect(self.connect_to_peer)
        self.disconnect_button.clicked.connect(self.disconnect_from_peer)

        self.websocket_thread = None
        self.ngrok_tunnel = None
        self.disconnect_button.setEnabled(False)

        self.kernel_manager = KernelManager()
        self.kernel_manager.start_kernel()
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()

        self.add_new_cell(None, send_message=False)

    def on_cell_text_changed(self, cell_widget):
        cell_id = cell_widget.cell_id
        content = cell_widget.input_area.toPlainText()
        
        for cell in self.notebook:
            if cell['id'] == cell_id:
                cell['source'] = content
                break
        
        if self.websocket_thread:
            message = {
                'action': 'update_cell_text',
                'cell_id': cell_id,
                'content': content
            }
            self.websocket_thread.send_message(json.dumps(message))

    def handle_websocket_message(self, message_str):
        try:
            message = json.loads(message_str)
            action = message.get('action')
            cell_id = message.get('cell_id')

            if action == 'initial_state':
                self._rebuild_ui_from_notebook_data(message.get('notebook', []))

            elif action == 'add_cell':
                after_cell_id = message.get('after_cell_id')
                new_cell_id = message.get('new_cell_id')
                self.add_new_cell(self.cell_widgets.get(after_cell_id), new_cell_id=new_cell_id, send_message=False)
            
            elif action == 'delete_cell':
                if cell_id in self.cell_widgets:
                    self.delete_cell(self.cell_widgets[cell_id], send_message=False)
            
            elif action == 'update_cell_text':
                if cell_id in self.cell_widgets:
                    content = message.get('content')
                    self.cell_widgets[cell_id].input_area.set_text_from_websocket(content)
        except json.JSONDecodeError as e:
            print(f"Error decoding message: {e}")

    def _rebuild_ui_from_notebook_data(self, notebook_data):
        for widget in self.cell_widgets.values():
            widget.deleteLater()
        self.cell_widgets.clear()
        self.notebook = []

        for cell_data in notebook_data:
            self.notebook.append(cell_data)
            widget = CellWidget(self, cell_data['id'], cell_type=cell_data['cell_type'], content=cell_data['source'])
            self.notebook_layout.addWidget(widget)
            self.cell_widgets[cell_data['id']] = widget
            widget.input_area.update_height()

    def add_new_cell(self, after_widget=None, new_cell_id=None, send_message=True):
        cell_id = new_cell_id or str(uuid.uuid4())
        cell_data = {'id': cell_id, 'cell_type': 'code', 'source': '', 'outputs': []}
        
        widget = CellWidget(self, cell_id, content='')
        
        if after_widget:
            index = self.notebook_layout.indexOf(after_widget) + 1
            self.notebook.insert(index, cell_data)
        else:
            index = len(self.notebook)
            self.notebook.append(cell_data)

        self.notebook_layout.insertWidget(index, widget)
        self.cell_widgets[cell_id] = widget
        widget.input_area.update_height()
        
        if send_message and self.websocket_thread:
            after_cell_id = after_widget.cell_id if after_widget else None
            message = {
                'action': 'add_cell',
                'new_cell_id': cell_id,
                'after_cell_id': after_cell_id
            }
            self.websocket_thread.send_message(json.dumps(message))

    def delete_cell(self, cell_widget, send_message=True):
        if len(self.notebook) <= 1:
            QMessageBox.warning(self, "Cannot Delete", "Cannot delete the last cell.")
            return

        cell_id = cell_widget.cell_id
        
        self.notebook = [cell for cell in self.notebook if cell['id'] != cell_id]
        cell_widget.deleteLater()
        del self.cell_widgets[cell_id]
        
        if send_message and self.websocket_thread:
            message = {
                'action': 'delete_cell',
                'cell_id': cell_id
            }
            self.websocket_thread.send_message(json.dumps(message))

    def run_code_in_cell(self, cell_widget):
        code = cell_widget.input_area.toPlainText()
        cell_widget.output_area.clear()
        cell_widget.output_area.setVisible(True)

        msg_id = self.kernel_client.execute(code)
        
        while True:
            try:
                msg = self.kernel_client.get_iopub_msg(timeout=1)
                if msg['parent_header'].get('msg_id') == msg_id:
                    msg_type = msg['header']['msg_type']
                    content = msg['content']
                    
                    if msg_type == 'stream':
                        cell_widget.output_area.append(content['text'])
                    elif msg_type == 'execute_result':
                        cell_widget.output_area.append(content['data'].get('text/plain', ''))
                    elif msg_type == 'error':
                        cell_widget.output_area.append('\n'.join(content['traceback']))
                    elif msg_type == 'status' and content['execution_state'] == 'idle':
                        break
            except Exception:
                break

    def get_notebook_state(self):
        return self.notebook

    def update_status(self, message):
        print(f"Status: {message}")
        QMessageBox.information(self, "Connection Status", message)

    def connect_to_peer(self):
        text, ok = QInputDialog.getText(self, 'Connect to Peer', 'Enter host URI (e.g., my-tunnel.ngrok-free.app)\nLeave empty to start a server.')
        if ok:
            uri = ""
            is_server = not bool(text)

            if not is_server:
                clean_text = text.replace("https://", "").replace("http://", "").replace("ws://", "").replace("wss://", "")
                uri = f"wss://{clean_text}"
            else:
                try:
                    self.ngrok_tunnel = ngrok.connect(8765, "http")
                    public_url = self.ngrok_tunnel.public_url.replace("https://", "").replace("http://", "")
                    self.update_status(f"Server running. Share this URI:\n{public_url}")
                except Exception as e:
                    QMessageBox.critical(self, "ngrok Error", f"Could not start ngrok tunnel: {e}")
                    return
            
            main_window_ref = self if is_server else None
            self.websocket_thread = WebsocketThread(uri=uri, main_window=main_window_ref)
            self.websocket_thread.message_received.connect(self.handle_websocket_message)
            self.websocket_thread.connection_status_changed.connect(self.update_status)
            self.websocket_thread.start()
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)

    def disconnect_from_peer(self):
        if self.ngrok_tunnel:
            ngrok.disconnect(self.ngrok_tunnel.public_url)
            self.ngrok_tunnel = None

        if self.websocket_thread:
            self.websocket_thread.stop()
            self.websocket_thread = None
            self.update_status("Disconnected")
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)

    def save_notebook(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "IPYNB Files (*.ipynb);;All Files (*)")
        if path:
            try:
                notebook_node = nbformat.v4.new_notebook()
                cells = []
                for cell_data in self.notebook:
                    cells.append(nbformat.v4.new_code_cell(cell_data['source']))
                notebook_node['cells'] = cells
                with open(path, 'w') as f:
                    nbformat.write(notebook_node, f)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {e}")
    
    def load_notebook(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "IPYNB Files (*.ipynb);;All Files (*)")
        if path:
            try:
                with open(path, 'r') as f:
                    notebook_node = nbformat.read(f, as_version=4)
                
                notebook_data = []
                for cell in notebook_node.cells:
                    cell_id = str(uuid.uuid4())
                    notebook_data.append({
                        'id': cell_id, 
                        'cell_type': cell.cell_type, 
                        'source': cell.source, 
                        'outputs': []
                    })
                
                self._rebuild_ui_from_notebook_data(notebook_data)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load file: {e}")

    def closeEvent(self, event):
        self.disconnect_from_peer()
        self.kernel_manager.shutdown_kernel()
        event.accept()

# --- 6. Application Entry Point ---
if __name__ == '__main__':
    NGROK_AUTHTOKEN = os.environ.get('NGROK_AUTHTOKEN') 
    if NGROK_AUTHTOKEN:
        ngrok.set_auth_token(NGROK_AUTHTOKEN)
    
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec_())
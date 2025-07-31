import sys
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QAction,
    QDialog, QVBoxLayout as QDialogVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QCursor

# Загружаем данные
main_table = pd.read_json(r'C:\Users\ivant\Desktop\proj\tren\leetcode\leetcode_problems.json')
main_table.set_index('questionId',inplace=True)

# --- Определим, какие столбцы хотим отображать ---
# Вы можете изменить этот список на нужные вам столбцы
COLUMNS_TO_DISPLAY = ['title', 'difficulty','categoryTitle'] # Пример, замените на реальные названия столбцов из вашего JSON

class FilterDialog(QDialog):
    """Диалоговое окно для ввода критерия фильтрации по одному столбцу."""
    def __init__(self, column_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Фильтр по столбцу '{column_name}'")
        self.setModal(True)
        self.resize(300, 100)

        self.layout = QVBoxLayout()

        self.label = QLabel(f"Введите значение для фильтрации по столбцу '{column_name}':")
        self.layout.addWidget(self.label)

        self.line_edit = QLineEdit()
        self.layout.addWidget(self.line_edit)

        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Применить")
        self.cancel_button = QPushButton("Отмена")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)

        self.layout.addLayout(self.button_layout)
        self.setLayout(self.layout)

    def get_filter_text(self):
        """Возвращает текст, введенный в поле фильтра."""
        return self.line_edit.text()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Приложение с вкладками и таблицей Pandas")
        self.setGeometry(100, 100, 1000, 700)

        # Храним исходные данные и текущие отфильтрованные данные
        self.full_data = pd.DataFrame() # Исходные данные с выбранными столбцами
        self.displayed_data = pd.DataFrame() # Данные, отображаемые в таблице (могут быть отфильтрованы)
        self.current_filters = {} # Словарь для хранения активных фильтров {column_name: filter_value}

        # Создаем виджет вкладок
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Создаем первую вкладку
        self.create_table_tab()

    def create_table_tab(self):
        """Создает вкладку с таблицей pandas и фильтром по столбцам."""
        tab = QWidget()
        layout = QVBoxLayout()

        # Используем глобальный main_table и фильтруем столбцы
        try:
            self.full_data = main_table[COLUMNS_TO_DISPLAY].copy()
            self.displayed_data = self.full_data.copy() # Изначально отображаем все
        except KeyError as e:
            print(f"Ошибка: Один или несколько указанных столбцов не найдены в DataFrame: {e}")
            print("Доступные столбцы:", main_table.columns.tolist())
            available_columns = [col for col in COLUMNS_TO_DISPLAY if col in main_table.columns]
            if available_columns:
                print(f"Отображаем доступные столбцы: {available_columns}")
                self.full_data = main_table[available_columns].copy()
                self.displayed_data = self.full_data.copy()
            else:
                print("Нет доступных столбцов для отображения из заданного списка.")
                self.full_data = pd.DataFrame()
                self.displayed_data = pd.DataFrame()

        print("Исходный DataFrame для отображения (первые 5 строк):")
        print(self.full_data.head())

        # Создаем QTableWidget
        self.table_widget = QTableWidget()
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu) # Включаем контекстное меню
        # Подключаем сигнал контекстного меню заголовка к слоту
        header = self.table_widget.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.open_header_context_menu)

        # Изначально заполняем таблицу
        self.update_table_display()

        layout.addWidget(self.table_widget)
        tab.setLayout(layout)

        self.tab_widget.addTab(tab, "Таблица данных")

    def open_header_context_menu(self, position: QPoint):
        """Открывает контекстное меню при правом клике по заголовку таблицы."""
        header = self.table_widget.horizontalHeader()
        # logicalIndex получает индекс логического столбца (с учетом сортировки/перемещения)
        column_logical_index = header.logicalIndexAt(position)

        # Проверяем, кликнули ли мы на заголовке (а не вне его)
        if column_logical_index >= 0:
            # Получаем название столбца по его логическому индексу
            # Учитываем, что первый столбец в таблице - это индекс из DataFrame
            if column_logical_index == 0:
                column_name = "Index" # Специальный случай для столбца индекса
            else:
                # Индекс в DataFrame на 1 меньше, так как 0-й столбец таблицы - это индекс DF
                df_column_index = column_logical_index - 1
                if df_column_index < len(self.full_data.columns):
                     column_name = self.full_data.columns[df_column_index]
                else:
                     return # На случай ошибки

            # Создаем контекстное меню
            context_menu = QMenu(self)

            # Действие для фильтрации
            filter_action = QAction(f"Фильтровать по '{column_name}'", self)
            filter_action.triggered.connect(lambda: self.show_filter_dialog(column_name))
            context_menu.addAction(filter_action)

            # Действие для сброса фильтра по этому столбцу (если фильтр активен)
            if column_name in self.current_filters:
                clear_filter_action = QAction(f"Сбросить фильтр по '{column_name}'", self)
                clear_filter_action.triggered.connect(lambda: self.clear_filter(column_name))
                context_menu.addAction(clear_filter_action)

            # Действие для сброса всех фильтров
            if self.current_filters:
                clear_all_filters_action = QAction("Сбросить все фильтры", self)
                clear_all_filters_action.triggered.connect(self.clear_all_filters)
                context_menu.addAction(clear_all_filters_action)

            # Отображаем меню в позиции курсора
            context_menu.exec_(QCursor.pos())

    def show_filter_dialog(self, column_name: str):
        """Показывает диалог фильтрации для указанного столбца."""
        dialog = FilterDialog(column_name, self)
        if dialog.exec_() == QDialog.Accepted:
            filter_text = dialog.get_filter_text()
            if filter_text is not None: # Даже пустая строка допустима как фильтр
                self.apply_filter(column_name, filter_text)

    def apply_filter(self, column_name: str, filter_text: str):
        """Применяет фильтр к данным и обновляет таблицу."""
        # Сохраняем фильтр
        self.current_filters[column_name] = filter_text
        print(f"Применен фильтр: {column_name} = '{filter_text}'")
        print("Активные фильтры:", self.current_filters)

        # Начинаем с полных данных
        filtered_data = self.full_data.copy()

        # Применяем все активные фильтры поочередно
        for col, value in self.current_filters.items():
            if col == "Index":
                # Особая обработка для индекса
                # Пробуем преобразовать фильтр в тип индекса (предположим int или str)
                try:
                    # Если индекс числовой, пытаемся фильтровать как число
                    if pd.api.types.is_integer_dtype(self.full_data.index):
                         filter_value_int = int(value)
                         filtered_data = filtered_data[filtered_data.index == filter_value_int]
                    else:
                         # Иначе фильтруем как строку
                         filtered_data = filtered_data[filtered_data.index.astype(str) == value]
                except ValueError:
                    # Если не удалось преобразовать в int, фильтруем как строку
                    filtered_data = filtered_data[filtered_data.index.astype(str) == value]
            else:
                # Фильтрация по обычным столбцам
                # Фильтруем строки, где значение в столбце содержит filter_text (без учета регистра)
                filtered_data = filtered_data[filtered_data[col].astype(str).str.contains(value, case=False, na=False)]

        self.displayed_data = filtered_data
        self.update_table_display()

    def clear_filter(self, column_name: str):
        """Сбрасывает фильтр по одному столбцу."""
        if column_name in self.current_filters:
            del self.current_filters[column_name]
            print(f"Сброшен фильтр по столбцу: {column_name}")
            self.reapply_all_filters() # Переприменить оставшиеся фильтры

    def clear_all_filters(self):
        """Сбрасывает все фильтры."""
        self.current_filters.clear()
        print("Все фильтры сброшены.")
        self.displayed_data = self.full_data.copy()
        self.update_table_display()

    def reapply_all_filters(self):
        """Переприменяет все оставшиеся фильтры."""
        # Начинаем с полных данных
        filtered_data = self.full_data.copy()

        # Применяем все активные фильтры
        for col, value in self.current_filters.items():
             if col == "Index":
                try:
                    if pd.api.types.is_integer_dtype(self.full_data.index):
                         filter_value_int = int(value)
                         filtered_data = filtered_data[filtered_data.index == filter_value_int]
                    else:
                         filtered_data = filtered_data[filtered_data.index.astype(str) == value]
                except ValueError:
                    filtered_data = filtered_data[filtered_data.index.astype(str) == value]
             else:
                filtered_data = filtered_data[filtered_data[col].astype(str).str.contains(value, case=False, na=False)]

        self.displayed_data = filtered_data
        self.update_table_display()

    def update_table_display(self):
        """Обновляет содержимое QTableWidget данными из self.displayed_data."""
        # Очищаем таблицу перед заполнением
        self.table_widget.clear()

        df = self.displayed_data

        if df.empty:
            self.table_widget.setRowCount(1)
            self.table_widget.setColumnCount(1)
            self.table_widget.setHorizontalHeaderLabels(["Нет данных"])
            self.table_widget.setItem(0, 0, QTableWidgetItem("Нет строк, соответствующих фильтрам."))
            self.table_widget.setSortingEnabled(False)
            return

        # Устанавливаем количество строк и столбцов (+1 для индекса)
        self.table_widget.setRowCount(df.shape[0])
        self.table_widget.setColumnCount(df.shape[1] + 1) # +1 для столбца индекса

        # Устанавливаем заголовки столбцов (индекс + названия столбцов из DataFrame)
        headers = ['Index'] + df.columns.tolist()
        self.table_widget.setHorizontalHeaderLabels(headers)

        # Включаем сортировку
        self.table_widget.setSortingEnabled(True)

        # Заполняем таблицу данными
        for i in range(df.shape[0]): # строки
            # Заполняем первый столбец (индекс)
            index_item = QTableWidgetItem(str(df.index[i]))
            index_item.setTextAlignment(Qt.AlignCenter)
            self.table_widget.setItem(i, 0, index_item) # Столбец 0 - индекс

            # Заполняем остальные столбцы данными из DataFrame
            for j in range(df.shape[1]): # столбцы данных
                value_str = str(df.iat[i, j])
                data_item = QTableWidgetItem(value_str)
                # data_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter) # Можно настроить
                self.table_widget.setItem(i, j + 1, data_item) # Столбцы данных начинаются с 1
        self.table_widget.resizeColumnsToContents()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

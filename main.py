"""실행 진입점 —  python main.py"""
import tkinter as tk

from src.app import LabelingApp

if __name__ == "__main__":
    root = tk.Tk()
    LabelingApp(root)
    root.mainloop()

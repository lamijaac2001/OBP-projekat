import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

PHASES = ["baseline", "indexes", "columnstore", "partition", "compression"]

class BenchmarkGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SQL Benchmark Tool")
        self.root.geometry("900x600")

        # Dropdown za izbor faze
        frame = ttk.Frame(root, padding=10)
        frame.pack(fill=tk.X)

        ttk.Label(frame, text="Odaberi fazu optimizacije:").pack(side=tk.LEFT, padx=5)
        self.phase_var = tk.StringVar()
        self.combo = ttk.Combobox(frame, textvariable=self.phase_var, values=PHASES, state="readonly")
        self.combo.pack(side=tk.LEFT, padx=5)

        # Dugme za pokretanje testa
        ttk.Button(frame, text="Pokreni test", command=self.run_phase).pack(side=tk.LEFT, padx=10)

        # Dugme za učitavanje rezultata
        ttk.Button(frame, text="Prikaži rezultate", command=self.show_results).pack(side=tk.LEFT, padx=10)

        # Status label
        self.status = tk.Label(root, text="Status: Čeka se odabir faze...", anchor="w")
        self.status.pack(fill=tk.X, pady=5)

        # Tabela rezultata
        self.tree = ttk.Treeview(root, columns=("query", "min", "max", "avg", "runs"), show="headings")
        self.tree.heading("query", text="Query")
        self.tree.heading("min", text="Min (ms)")
        self.tree.heading("max", text="Max (ms)")
        self.tree.heading("avg", text="Avg (ms)")
        self.tree.heading("runs", text="Runs")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Graf placeholder
        self.canvas = None

    def run_phase(self):
        phase = self.phase_var.get()
        if not phase:
            messagebox.showerror("Greška", "Molimo odaberite fazu!")
            return

        self.status.config(text=f"Pokrećem benchmark za fazu: {phase}...")
        self.root.update_idletasks()

        try:
            subprocess.run(["python", "benchmark_suite.py", "--phase", phase], check=True)
            self.status.config(text=f"✅ Test završen za fazu: {phase}. Rezultati spremljeni u CSV/PNG.")
        except subprocess.CalledProcessError as e:
            self.status.config(text=f"❌ Greška pri pokretanju testa: {e}")

    def show_results(self):
        phase = self.phase_var.get()
        if not phase:
            messagebox.showerror("Greška", "Molimo odaberite fazu!")
            return

        csv_file = f"results_{phase}.csv"
        if not os.path.exists(csv_file):
            messagebox.showwarning("Upozorenje", f"Nema rezultata za fazu '{phase}'. Pokreni test prvo.")
            return

        try:
            # Učitavanje CSV rezultata
            df = pd.read_csv(csv_file, sep=",")
        except Exception as e:
            messagebox.showerror("Greška", f"Ne mogu učitati {csv_file}: {e}")
            return

        # Debug info
        print("\n=== CSV DEBUG ===")
        print(df.head())
        messagebox.showinfo("Debug", f"Učitano {len(df)} redova iz {csv_file}")

        # Brisanje stare tabele
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Punjenje nove tabele
        for _, row in df.iterrows():
            print("Red:", row.to_dict())  # debug ispis
            try:
                min_val = f"{float(row['min_time_ms']):.2f}"
                max_val = f"{float(row['max_time_ms']):.2f}"
                avg_val = f"{float(row['avg_time_ms']):.2f}"
            except Exception:
                min_val = row.get("min_time_ms", "")
                max_val = row.get("max_time_ms", "")
                avg_val = row.get("avg_time_ms", "")

            self.tree.insert("", tk.END, values=(row.get("query", "")[:40] + "...", 
                                                 min_val, 
                                                 max_val, 
                                                 avg_val, 
                                                 row.get("runs", "")))

        # Crtanje grafa
        if self.canvas:
            self.canvas.get_tk_widget().destroy()

        if not df.empty:
            fig, ax = plt.subplots(figsize=(7, 4))
            ax.bar(df["query"], df["avg_time_ms"])
            ax.set_ylabel("Avg vrijeme (ms)")
            ax.set_title(f"Performanse SQL upita – {phase}")
            ax.tick_params(axis="x", rotation=45)

            self.canvas = FigureCanvasTkAgg(fig, master=self.root)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = BenchmarkGUI(root)
    root.mainloop()


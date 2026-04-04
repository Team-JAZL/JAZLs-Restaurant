"""JAZL's Restaurant

GROUP 1: JAZL
    Members: Cabales, Lean Vince A.
             Calix, Zuriel Eliazar D.
             Escrupulo, Ma. Asherah Francine Faith S.
             Porras, Jessie Loraine P. 
             
    Topic: Basic Message Queue
    Description: This code demonstrates a simple implementation of a basic message queue using
                 a restaurant order system analogy that receives orders in a FIFO basis.


This file is a minimal entry point that starts the Tkinter UI. The
application logic has been split across modules to keep the UI, queue,
order model, and kitchen logic separate and easy to understand.
"""

import tkinter as tk
from ui import RestaurantOrderApp


if __name__ == "__main__":
    root = tk.Tk()
    app = RestaurantOrderApp(root)
    root.mainloop()

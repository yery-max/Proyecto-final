# -----------------------------------------------------------------------------
# main.py - Sistema de Inventario Empresarial v3.3 (Versión de Entrega Final)
# Autor: M.Sc, Eng. Jim Requena (conceptualización), Coding Partner (implementación)
#
# Descripción:
# Esta es la versión es estable y completamente funcional del sistema.
# Incluye la corrección del bug de eliminación de productos y ajustes finales
# de interfaz para una experiencia de usuario robusta.
# -----------------------------------------------------------------------------

# --- 1. IMPORTACIONES: Las herramientas que necesitamos ---
import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.toast import ToastNotification
import json
import os
import csv
import webbrowser
from datetime import datetime
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

# --- 2. EL CEREBRO: La lógica de negocio del sistema ---
class SistemaInventario:
    """
    Maneja todas las operaciones de datos del sistema (el backend).
    Esta clase no sabe nada sobre la interfaz gráfica, solo se encarga
    de la lógica de negocio, cumpliendo con la separación de responsabilidades.
    """
    def __init__(self):
        """
        Constructor de la clase. Se ejecuta una sola vez al crear el objeto.
        Aquí se inicializa el 'estado' de la aplicación: las listas y
        diccionarios que contendrán todos nuestros datos en memoria.
        """
        self.productos = []
        self.sucursales = {}
        self.ventas = []
        self.config = {"stock_minimo_alerta": 10}
        os.makedirs('data', exist_ok=True)
        self.cargar_datos()

    def cargar_datos(self):
        """
        Responsable de la persistencia de datos (RNF1).
        Carga el estado del sistema desde archivos JSON. Si no existen,
        activa la configuración inicial.
        """
        try:
            with open('data/sucursales.json', 'r', encoding='utf-8') as f: self.sucursales = json.load(f)
            with open('data/inventario.json', 'r', encoding='utf-8') as f: self.productos = json.load(f)
            if not self.sucursales: self._configuracion_inicial()
        except (FileNotFoundError, json.JSONDecodeError):
            self._configuracion_inicial()
        
        try:
            with open('data/ventas.json', 'r', encoding='utf-8') as f: self.ventas = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): self.ventas = []

    def _configuracion_inicial(self):
        """
        Flujo de primera ejecución. Busca un CSV y, si no, crea datos de ejemplo.
        """
        path_csv_inicial = 'data/productos_iniciales.csv'
        if os.path.exists(path_csv_inicial):
            print(f"Archivo '{path_csv_inicial}' encontrado, cargando datos...")
            self.procesar_carga_csv(path_csv_inicial)
        else:
            print("No se encontró 'productos_iniciales.csv'. Creando datos de ejemplo...")
            self._crear_datos_de_ejemplo()

    def _crear_datos_de_ejemplo(self):
        """Crea un conjunto de datos para que la app sea funcional al instante."""
        self.sucursales = {"Centro": {}, "Norte": {}, "Sur": {}}
        self.productos = [
            {'sku': 'TEC-001', 'nombre': 'Teclado Mecanico', 'precio': 89.99, 'stock': 15, 'sucursal': 'Centro'},
            {'sku': 'MOU-001', 'nombre': 'Mouse Gamer RGB', 'precio': 45.50, 'stock': 35, 'sucursal': 'Centro'},
            {'sku': 'TEC-001', 'nombre': 'Teclado Mecanico', 'precio': 89.99, 'stock': 8, 'sucursal': 'Norte'},
        ]
        self.guardar_datos()

    def guardar_datos(self):
        """
        RNF1: Guarda el estado actual de los datos en los archivos JSON.
        --- Decisión de Formato: ¿Por qué JSON? ---
        Elegimos JSON porque es legible por humanos (ideal para depurar), es ligero
        y es el estándar de facto para el intercambio de datos en la web. Esto
        facilita una futura migración a una aplicación web.
        """
        try:
            with open('data/inventario.json', 'w', encoding='utf-8') as f: json.dump(self.productos, f, indent=4)
            with open('data/sucursales.json', 'w', encoding='utf-8') as f: json.dump(self.sucursales, f, indent=4)
            with open('data/ventas.json', 'w', encoding='utf-8') as f: json.dump(self.ventas, f, indent=4)
        except Exception as e:
            print(f"Ocurrió un error al guardar los datos: {e}")

    def buscar_producto_por_sku_y_sucursal(self, sku, sucursal):
        """
        RF1.2: Localiza un producto por su clave única (SKU + Sucursal).
        --- Decisión de Algoritmo: Bucle 'for' vs. Comprensión de Lista ---
        Usamos un bucle 'for' tradicional aquí porque es más eficiente. Necesitamos
        encontrar solo UN producto y detener la búsqueda tan pronto como lo hagamos
        ('return p'). Una comprensión de lista recorrería TODA la lista sin necesidad.
        """
        for p in self.productos:
            if p.get('sku') == sku and p.get('sucursal') == sucursal:
                return p
        return None

    def procesar_carga_csv(self, archivo_path):
        """
        RF5.1: Procesa un CSV. Si el producto existe, suma stock; si no, lo crea.
        """
        try:
            with open(archivo_path, mode='r', encoding='utf-8') as f:
                lector = csv.DictReader(f)
                creados, actualizados = 0, 0
                for fila in lector:
                    if fila['sucursal'] not in self.sucursales:
                        self.sucursales[fila['sucursal']] = {}
                    
                    producto_existente = self.buscar_producto_por_sku_y_sucursal(fila['sku'], fila['sucursal'])
                    if producto_existente:
                        producto_existente['stock'] += int(fila['stock'])
                        actualizados += 1
                    else:
                        self.agregar_producto(fila['sku'], fila['nombre'], float(fila['precio']), int(fila['stock']), fila['sucursal'])
                        creados += 1
            self.guardar_datos()
            return True, f"{creados} creados, {actualizados} actualizados."
        except Exception as e:
            return False, f"Error al leer el CSV: {e}"

    def agregar_producto(self, sku, nombre, precio, stock, sucursal):
        """RF1.1: Lógica para crear un nuevo registro de producto."""
        if self.buscar_producto_por_sku_y_sucursal(sku, sucursal):
            return False, f"SKU {sku} ya existe en {sucursal}."
        self.productos.append({'id': str(uuid.uuid4()),'sku': sku,'nombre': nombre,'precio': float(precio),'stock': int(stock),'sucursal': sucursal})
        self.guardar_datos()
        return True, "Producto agregado."

    def editar_producto(self, sku, sucursal, nuevos_datos):
        """RF1.1: Lógica para actualizar un producto existente."""
        producto = self.buscar_producto_por_sku_y_sucursal(sku, sucursal)
        if producto:
            producto.update(nuevos_datos)
            self.guardar_datos()
            return True
        return False

    def eliminar_producto(self, sku, sucursal):
        """RF1.1: Lógica para eliminar un producto."""
        producto = self.buscar_producto_por_sku_y_sucursal(sku, sucursal)
        if producto:
            self.productos.remove(producto)
            self.guardar_datos()
            return True
        return False

    def registrar_venta(self, items_venta, sucursal, total):
        """
        RF3.3, RF3.4, RF3.5: Valida stock, lo descuenta de la sucursal correcta
        y registra la transacción.
        """
        for item in items_venta:
            producto = self.buscar_producto_por_sku_y_sucursal(item['sku'], sucursal)
            if not producto or producto['stock'] < item['cantidad']:
                self.cargar_datos(); return False, [], None
        
        productos_con_stock_bajo = []
        for item in items_venta:
            producto = self.buscar_producto_por_sku_y_sucursal(item['sku'], sucursal)
            producto['stock'] -= item['cantidad']
            if producto['stock'] <= self.config["stock_minimo_alerta"]:
                productos_con_stock_bajo.append(producto)
        
        nueva_venta = {'id': f"VTA-{uuid.uuid4().hex[:6].upper()}", 'fecha': datetime.now().isoformat(), 'items': items_venta, 'sucursal': sucursal, 'total': total}
        self.ventas.append(nueva_venta)
        self.guardar_datos()
        return True, productos_con_stock_bajo, nueva_venta['id']

    def transferir_productos(self, sku, cantidad, origen, destino):
        """RF2.2, RF2.3: Lógica para transferir stock entre sucursales."""
        prod_origen = self.buscar_producto_por_sku_y_sucursal(sku, origen)
        if not prod_origen: return False, f"Producto no encontrado en {origen}."
        if prod_origen['stock'] < cantidad: return False, f"Stock insuficiente en {origen}."
        
        prod_destino = self.buscar_producto_por_sku_y_sucursal(sku, destino)
        prod_origen['stock'] -= cantidad
        if prod_destino:
            prod_destino['stock'] += cantidad
        else:
            nuevo_prod_destino = prod_origen.copy()
            nuevo_prod_destino.update({'id': str(uuid.uuid4()), 'sucursal': destino, 'stock': cantidad})
            self.productos.append(nuevo_prod_destino)
        
        self.guardar_datos()
        return True, f"Transferencia de {cantidad} u. de {sku} de {origen} a {destino} exitosa."
    
    def reinicializar_sistema(self):
        """RF5.2: Elimina todos los datos transaccionales del sistema."""
        self.productos = []; self.ventas = []; self.sucursales = {}
        self.guardar_datos()
        return True, "Sistema reinicializado."

    def generar_reporte_inventario(self, sucursal_id=None):
        """Genera un reporte PDF del inventario actual, opcionalmente filtrado por sucursal."""
        os.makedirs('reports', exist_ok=True)
        nombre_sucursal = sucursal_id if sucursal_id else "Todas"
        nombre_archivo = f"reports/reporte_inventario_{nombre_sucursal}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        productos_reporte = self.productos
        if sucursal_id:
            productos_reporte = [p for p in self.productos if p['sucursal'] == sucursal_id]

        c = canvas.Canvas(nombre_archivo, pagesize=letter)
        width, height = letter
        c.setFont("Helvetica-Bold", 16)
        c.drawString(inch, height - inch, f"Reporte de Inventario - Sucursal: {nombre_sucursal}")
        y = height - inch - 40
        
        if not productos_reporte:
            c.setFont("Helvetica", 12)
            c.drawString(inch, y, "No hay productos en el inventario para esta selección.")
        else:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(inch, y, "SKU"); c.drawString(inch * 2.5, y, "Nombre"); c.drawString(inch * 5, y, "Stock"); c.drawString(inch * 6, y, "Precio")
            y -= 20
            c.setFont("Helvetica", 10)
            for p in productos_reporte:
                c.drawString(inch, y, p['sku']); c.drawString(inch * 2.5, y, p['nombre']); c.drawString(inch * 5, y, str(p['stock'])); c.drawString(inch * 6, y, f"${p['precio']:.2f}")
                y -= 20
                if y < inch: # Salto de página
                    c.showPage(); y = height - inch
                    c.setFont("Helvetica-Bold", 10); c.drawString(inch, y, "SKU"); c.drawString(inch * 2.5, y, "Nombre"); c.drawString(inch * 5, y, "Stock"); c.drawString(inch * 6, y, "Precio"); y -= 20
                    c.setFont("Helvetica", 10)
        
        c.save()
        return nombre_archivo

    def generar_recibo_venta_pdf(self, venta_id):
        """RF4.1: Crea un PDF como comprobante para una venta específica."""
        venta = next((v for v in self.ventas if v['id'] == venta_id), None)
        if not venta: return None, "Venta no encontrada."
        
        os.makedirs('reports', exist_ok=True)
        nombre_archivo = f"reports/recibo_{venta_id}.pdf"
        c = canvas.Canvas(nombre_archivo, pagesize=letter)
        width, height = letter
        c.setFont("Helvetica-Bold", 18); c.drawString(inch, height - inch, "Recibo de Venta")
        c.setFont("Helvetica", 10)
        c.drawString(inch, height - inch - 20, f"ID Venta: {venta['id']}")
        fecha = datetime.fromisoformat(venta['fecha']).strftime('%d/%m/%Y %H:%M:%S')
        c.drawString(inch, height - inch - 35, f"Fecha: {fecha}")
        c.drawString(inch, height - inch - 50, f"Sucursal: {venta['sucursal']}")
        y = height - inch - 80
        c.setFont("Helvetica-Bold", 10)
        c.drawString(inch, y, "SKU"); c.drawString(inch * 2, y, "Producto"); c.drawString(inch * 4.5, y, "Cantidad"); c.drawString(inch * 5.5, y, "Precio Unit."); c.drawString(inch * 6.5, y, "Subtotal")
        y -= 15; c.line(inch, y, width - inch, y); y -= 15
        c.setFont("Helvetica", 10)
        for item in venta['items']:
            c.drawString(inch, y, item['sku']); c.drawString(inch * 2, y, item['nombre']); c.drawString(inch * 4.5, y, str(item['cantidad'])); c.drawString(inch * 5.5, y, f"${item['precio_unitario']:.2f}"); c.drawString(inch * 6.5, y, f"${item['subtotal']:.2f}")
            y -= 20
        y -= 10; c.line(inch * 5, y, width - inch, y); y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(inch * 5.5, y, "TOTAL:"); c.drawString(inch * 6.5, y, f"${venta['total']:.2f}")
        c.save()
        return nombre_archivo, "Recibo generado."

    def generar_reporte_cierre_diario(self):
        """RF4.2: Crea un PDF con el resumen de ventas del día."""
        os.makedirs('reports', exist_ok=True)
        hoy_str = datetime.now().strftime('%Y-%m-%d')
        nombre_archivo = f"reports/cierre_diario_{hoy_str}.pdf"
        ventas_hoy = [v for v in self.ventas if v['fecha'].startswith(hoy_str)]
        
        c = canvas.Canvas(nombre_archivo, pagesize=letter)
        width, height = letter
        c.setFont("Helvetica-Bold", 18); c.drawString(inch, height - inch, f"Reporte de Cierre de Ventas - {hoy_str}")
        if not ventas_hoy:
            c.setFont("Helvetica", 12); c.drawString(inch, height - inch - 40, "No se registraron ventas en esta fecha.")
        else:
            total_ventas_dia = sum(v['total'] for v in ventas_hoy)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(inch, height - inch - 40, f"Total de Ventas del Día: ${total_ventas_dia:.2f}")
            c.drawString(inch, height - inch - 60, f"Número de Transacciones: {len(ventas_hoy)}")
            y = height - inch - 90
            c.setFont("Helvetica-Bold", 10); c.drawString(inch, y, "ID Venta"); c.drawString(inch * 2.5, y, "Sucursal"); c.drawString(inch * 4, y, "Total"); y -= 15
            c.setFont("Helvetica", 10)
            for v in ventas_hoy:
                c.drawString(inch, y, v['id']); c.drawString(inch * 2.5, y, v['sucursal']); c.drawString(inch * 4, y, f"${v['total']:.2f}"); y -= 20
                if y < inch: c.showPage(); y = height - inch
        
        c.setFont("Helvetica-Oblique", 9); c.drawString(inch, inch, f"Reporte generado a las {datetime.now().strftime('%H:%M:%S')}")
        c.save()
        return nombre_archivo

# --- 3. LA CARA: La interfaz gráfica de usuario (GUI) ---
class App:
    def __init__(self, root):
        self.sistema = SistemaInventario()
        self.root = root
        self.root.title("Sistema de Inventario Empresarial v3.4")
        self.root.geometry("1400x900")

        style = ttk.Style.get_instance()
        style.configure("Treeview", rowheight=25)
        style.map('Treeview', background=[('selected', '#2a52be')])

        self.crear_menu_y_statusbar()
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=5, padx=10, fill="both", expand=True)

        self.crear_pestaña_dashboard()
        self.crear_pestaña_inventario()
        self.crear_pestaña_ventas()
        self.crear_pestaña_transferencias()
        self.crear_pestaña_sistema()
        
        self.actualizar_filtros_sucursal()
        self.actualizar_lista_productos()
        self.actualizar_dashboard()

        self.cierre_realizado_hoy = False
        self.chequear_cierre_automatico()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        if tk.messagebox.askyesno("Salir", "¿Seguro que quieres cerrar?\nSe generará el reporte de cierre diario."):
            self.sistema.generar_reporte_cierre_diario()
            self.root.destroy()

    def chequear_cierre_automatico(self):
        ahora = datetime.now()
        if ahora.hour == 3 and ahora.minute == 0 and not self.cierre_realizado_hoy:
            self.cierre_realizado_hoy = True
            self.sistema.generar_reporte_cierre_diario()
            self.root.destroy()
        else:
            self.root.after(60000, self.chequear_cierre_automatico)
    
    def crear_menu_y_statusbar(self):
        menubar = tk.Menu(self.root); self.root.config(menu=menubar)
        menu_ayuda = tk.Menu(menubar, tearoff=0); menubar.add_cascade(label="Ayuda", menu=menu_ayuda)
        menu_ayuda.add_command(label="Acerca de...", command=self.mostrar_acerca_de)
        statusbar_frame = ttk.Frame(self.root, bootstyle="secondary"); statusbar_frame.pack(side="bottom", fill="x")
        ttk.Label(statusbar_frame, text="© 2025 M.Sc, Eng. Jim Requena. Prohibida la reproducción para fines comerciales.", padding=(10, 5), bootstyle="inverse-secondary").pack()

    def mostrar_acerca_de(self):
        messagebox.showinfo("Acerca de...", "Sistema de Inventario v3.4\n\n© 2025 M.Sc, Eng. Jim Requena.\nContacto para licencias: +591 75009349.")
    
    def crear_pestaña_dashboard(self):
        frame = ttk.Frame(self.notebook, padding=(10)); self.notebook.add(frame, text='📊 Dashboard')
        header_label = ttk.Label(frame, text="Resumen del Sistema", font=("Helvetica", 16, "bold")); header_label.pack(pady=10)
        filtro_dash_frame = ttk.Frame(frame); filtro_dash_frame.pack(pady=10)
        ttk.Label(filtro_dash_frame, text="Ver datos de sucursal:").pack(side='left', padx=5)
        self.filtro_sucursal_dash_var = tk.StringVar(value="Todas")
        self.filtro_sucursal_dash_combo = ttk.Combobox(filtro_dash_frame, textvariable=self.filtro_sucursal_dash_var, state="readonly"); self.filtro_sucursal_dash_combo.pack(side='left', padx=5)
        self.filtro_sucursal_dash_combo.bind("<<ComboboxSelected>>", self.actualizar_dashboard)
        kpi_frame = ttk.Frame(frame); kpi_frame.pack(pady=20, fill='x')
        self.meter_productos = ttk.Meter(kpi_frame, metersize=180, padding=10, amountused=0, metertype='semi', subtext='Productos Únicos', interactive=False, bootstyle='primary'); self.meter_productos.pack(side='left', expand=True, padx=20)
        self.meter_stock = ttk.Meter(kpi_frame, metersize=180, padding=10, amountused=0, metertype='semi', subtext='Unidades Totales', interactive=False, bootstyle='success'); self.meter_stock.pack(side='left', expand=True, padx=20)
        self.meter_bajo_stock = ttk.Meter(kpi_frame, metersize=180, padding=10, amountused=0, metertype='semi', subtext='Productos con Bajo Stock', interactive=False, bootstyle='danger'); self.meter_bajo_stock.pack(side='left', expand=True, padx=20)

    def actualizar_dashboard(self, event=None):
        sucursal_filtrada = self.filtro_sucursal_dash_var.get()
        productos_a_evaluar = self.sistema.productos if sucursal_filtrada == "Todas" else [p for p in self.sistema.productos if p['sucursal'] == sucursal_filtrada]
        total_productos = len({p['sku'] for p in productos_a_evaluar})
        total_unidades = sum(p.get('stock', 0) for p in productos_a_evaluar)
        productos_bajos = sum(1 for p in productos_a_evaluar if p.get('stock', 0) <= self.sistema.config['stock_minimo_alerta'])
        self.meter_productos.configure(amountused=total_productos); self.meter_stock.configure(amountused=total_unidades); self.meter_bajo_stock.configure(amountused=productos_bajos)

    def crear_pestaña_inventario(self):
        frame = ttk.Frame(self.notebook, padding=(10)); self.notebook.add(frame, text='📦 Gestión de Inventario')
        top_frame = ttk.Frame(frame); top_frame.pack(fill='x')
        filtro_frame = ttk.LabelFrame(top_frame, text="Filtros", padding=10); filtro_frame.pack(side='left', fill='y', padx=(0,10))
        ttk.Label(filtro_frame, text="Ver inventario de:").pack(pady=5)
        self.filtro_sucursal_var = tk.StringVar(value="Todas")
        self.filtro_sucursal_combo = ttk.Combobox(filtro_frame, textvariable=self.filtro_sucursal_var, state="readonly"); self.filtro_sucursal_combo.pack(pady=5)
        self.filtro_sucursal_combo.bind("<<ComboboxSelected>>", self.actualizar_lista_productos)
        form_frame = ttk.LabelFrame(top_frame, text="Detalles del Producto", padding=(15)); form_frame.pack(side='left', fill='x', expand=True)
        labels = ["SKU:", "Nombre:", "Precio:", "Stock:", "Sucursal:"]; self.entries = {}
        for i, label in enumerate(labels):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky='w')
            entry = ttk.Entry(form_frame, width=40); entry.grid(row=i, column=1, padx=5, pady=5, sticky='ew'); self.entries[label.lower().replace(':', '')] = entry
        btn_frame = ttk.Frame(form_frame); btn_frame.grid(row=len(labels), column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Agregar", command=self.agregar_producto_gui, bootstyle='success').pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Guardar", command=self.editar_producto_gui, bootstyle='info').pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Limpiar", command=self.limpiar_formulario, bootstyle='secondary').pack(side='left', padx=5)
        table_frame = ttk.LabelFrame(frame, text="Lista de Productos", padding=(15)); table_frame.pack(fill='both', expand=True, pady=10)
        columnas = ("sku", "nombre", "precio", "stock", "sucursal"); self.tree_inventario = ttk.Treeview(table_frame, columns=columnas, show='headings')
        for col in columnas: self.tree_inventario.heading(col, text=col.capitalize()); self.tree_inventario.column(col, width=150, anchor='center')
        self.tree_inventario.pack(fill='both', expand=True, side='left')
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree_inventario.yview); self.tree_inventario.configure(yscrollcommand=scrollbar.set); scrollbar.pack(fill='y', side='right')
        self.tree_inventario.bind('<<TreeviewSelect>>', self.seleccionar_producto)
        bottom_buttons_frame = ttk.Frame(frame); bottom_buttons_frame.pack(fill='x', pady=10, side='bottom')
        ttk.Button(bottom_buttons_frame, text="Eliminar Producto Seleccionado", command=self.eliminar_producto_gui, bootstyle='danger').pack(side='left', expand=True, padx=5)
        ttk.Button(bottom_buttons_frame, text="Generar Reporte de Inventario (PDF)", command=self.generar_reporte_inventario_gui, bootstyle='info-outline').pack(side='left', expand=True, padx=5)

    def actualizar_lista_productos(self, event=None):
        for item in self.tree_inventario.get_children(): self.tree_inventario.delete(item)
        sucursal_filtrada = self.filtro_sucursal_var.get()
        for p in self.sistema.productos:
            if sucursal_filtrada == "Todas" or p['sucursal'] == sucursal_filtrada:
                self.tree_inventario.insert('', 'end', values=(p['sku'], p['nombre'], f"{p['precio']:.2f}", p['stock'], p['sucursal']))

    def actualizar_filtros_sucursal(self):
        sucursales = sorted(list(self.sistema.sucursales.keys()))
        if not sucursales: sucursales = ["Default"]
        self.filtro_sucursal_combo['values'] = ["Todas"] + sucursales
        self.filtro_sucursal_dash_combo['values'] = ["Todas"] + sucursales
        self.venta_sucursal_combo['values'] = sucursales
        self.transfer_origen['values'] = sucursales
        self.transfer_destino['values'] = sucursales
        if sucursales and sucursales[0] != "Default": self.venta_sucursal_combo.current(0)
    
    def seleccionar_producto(self, event):
        seleccion = self.tree_inventario.selection()
        if not seleccion: return
        item = self.tree_inventario.item(seleccion[0]); valores = item['values']
        self.limpiar_formulario(limpiar_seleccion=False)
        self.entries['sku'].insert(0, valores[0]); self.entries['nombre'].insert(0, valores[1]); self.entries['precio'].insert(0, valores[2]); self.entries['stock'].insert(0, valores[3]); self.entries['sucursal'].insert(0, valores[4])
        self.entries['sku'].config(state='disabled'); self.entries['sucursal'].config(state='disabled')

    def limpiar_formulario(self, limpiar_seleccion=True):
        self.entries['sku'].config(state='normal'); self.entries['sucursal'].config(state='normal')
        for entry in self.entries.values(): entry.delete(0, 'end')
        if limpiar_seleccion and self.tree_inventario.selection():
            self.tree_inventario.selection_remove(self.tree_inventario.selection())
    
    def agregar_producto_gui(self):
        datos = {k: v.get() for k in self.entries};
        if not all([datos['sku'], datos['nombre'], datos['sucursal']]): Messagebox.show_error("SKU, Nombre y Sucursal son obligatorios.", "Error"); return
        try: precio = float(datos['precio']); stock = int(datos['stock'])
        except ValueError: Messagebox.show_error("Precio y Stock deben ser números.", "Error"); return
        exito, msg = self.sistema.agregar_producto(datos['sku'], datos['nombre'], precio, stock, datos['sucursal'])
        if exito: self.mostrar_toast("Éxito", msg, 'success'); self.actualizar_todo()
        else: Messagebox.show_error(msg, "Error")
            
    def editar_producto_gui(self):
        sku = self.entries['sku'].get(); sucursal = self.entries['sucursal'].get()
        if not sku: Messagebox.show_warning("Selecciona un producto para editar.", "Sin Selección"); return
        try: nuevos_datos = {'nombre': self.entries['nombre'].get(), 'precio': float(self.entries['precio'].get()), 'stock': int(self.entries['stock'].get())}
        except ValueError: Messagebox.show_error("Precio y Stock deben ser números.", "Error"); return
        if self.sistema.editar_producto(sku, sucursal, nuevos_datos):
            self.mostrar_toast("Éxito", "Producto actualizado.", 'info'); self.actualizar_todo()
        else: Messagebox.show_error("No se pudo actualizar.", "Error")
            
    def eliminar_producto_gui(self):
        seleccion = self.tree_inventario.selection()
        if not seleccion: Messagebox.show_warning("Selecciona un producto de la tabla para eliminar.", "Sin Selección"); return
        item = self.tree_inventario.item(seleccion[0]); sku, sucursal = item['values'][0], item['values'][4]
        if tk.messagebox.askyesno("Confirmar", f"¿Seguro que quieres eliminar el producto {sku} de la sucursal {sucursal}?"):
            if self.sistema.eliminar_producto(sku, sucursal):
                self.mostrar_toast("Éxito", "Producto eliminado.", 'danger'); self.actualizar_todo()
            else: Messagebox.show_error("No se pudo eliminar el producto.", "Error")

    def generar_reporte_inventario_gui(self):
        sucursal = self.filtro_sucursal_var.get()
        if sucursal == "Todas": sucursal = None
        archivo = self.sistema.generar_reporte_inventario(sucursal_id=sucursal)
        if archivo: Messagebox.show_info(f"Reporte de inventario generado en:\n{archivo}", "Reporte Generado")
            
    def crear_pestaña_ventas(self):
        frame = ttk.Frame(self.notebook, padding=(10)); self.notebook.add(frame, text='🛒 Punto de Venta'); self.venta_actual = []
        seleccion_frame = ttk.LabelFrame(frame, text="Añadir Producto a la Venta", padding=(10)); seleccion_frame.pack(side='left', fill='y', padx=(0,10))
        ttk.Label(seleccion_frame, text="Vender en Sucursal:").pack(fill='x', pady=2)
        self.venta_sucursal_combo = ttk.Combobox(seleccion_frame, state="readonly"); self.venta_sucursal_combo.pack(fill='x', pady=2)
        ttk.Label(seleccion_frame, text="SKU:").pack(fill='x', pady=2); self.venta_sku_entry = ttk.Entry(seleccion_frame); self.venta_sku_entry.pack(fill='x', pady=2)
        ttk.Label(seleccion_frame, text="Cantidad:").pack(fill='x', pady=2); self.venta_cantidad_entry = ttk.Entry(seleccion_frame); self.venta_cantidad_entry.pack(fill='x', pady=2)
        ttk.Button(seleccion_frame, text="Añadir al Carrito", command=self.agregar_a_venta_gui).pack(pady=10)
        carrito_frame = ttk.LabelFrame(frame, text="Carrito de Venta Actual", padding=(10)); carrito_frame.pack(side='right', fill='both', expand=True)
        columnas_venta = ("sku", "nombre", "cantidad", "precio_unit", "subtotal"); self.tree_venta = ttk.Treeview(carrito_frame, columns=columnas_venta, show='headings')
        for col in columnas_venta: self.tree_venta.heading(col, text=col.replace('_', ' ').capitalize())
        self.tree_venta.pack(fill='both', expand=True)
        total_frame = ttk.Frame(carrito_frame); total_frame.pack(fill='x', pady=10)
        self.total_label = ttk.Label(total_frame, text="Total: $0.00", font=("Helvetica", 14, "bold")); self.total_label.pack(side='left')
        ttk.Button(total_frame, text="Confirmar Venta", command=self.confirmar_venta_gui, bootstyle='success').pack(side='right')

    def agregar_a_venta_gui(self):
        sku = self.venta_sku_entry.get(); sucursal = self.venta_sucursal_combo.get()
        try: cantidad = int(self.venta_cantidad_entry.get())
        except ValueError: Messagebox.show_error("La cantidad debe ser un número.", "Error"); return
        if not all([sku, sucursal]) or cantidad <= 0: Messagebox.showerror("SKU, Sucursal y Cantidad son requeridos.", "Error"); return
        producto = self.sistema.buscar_producto_por_sku_y_sucursal(sku, sucursal)
        if not producto: Messagebox.showerror(f"Producto no encontrado en {sucursal}.", "Error"); return
        if producto['stock'] < cantidad: Messagebox.showwarning(f"Solo quedan {producto['stock']} unidades.", "Stock Insuficiente"); return
        item_venta = {'sku': sku, 'nombre': producto['nombre'], 'cantidad': cantidad, 'precio_unitario': producto['precio'], 'subtotal': producto['precio'] * cantidad}
        self.venta_actual.append(item_venta); self.actualizar_carrito_gui(); self.venta_sku_entry.delete(0, 'end'); self.venta_cantidad_entry.delete(0, 'end')

    def actualizar_carrito_gui(self):
        for item in self.tree_venta.get_children(): self.tree_venta.delete(item)
        total = 0
        for item in self.venta_actual:
            self.tree_venta.insert('', 'end', values=(item['sku'], item['nombre'], item['cantidad'], f"${item['precio_unitario']:.2f}", f"${item['subtotal']:.2f}")); total += item['subtotal']
        self.total_label.config(text=f"Total: ${total:.2f}")

    def confirmar_venta_gui(self):
        if not self.venta_actual: Messagebox.showerror("El carrito está vacío.", "Error"); return
        sucursal = self.venta_sucursal_combo.get()
        if not sucursal: Messagebox.showerror("Debe seleccionar una sucursal.", "Error"); return
        total = sum(item['subtotal'] for item in self.venta_actual)
        exito, productos_bajos, venta_id = self.sistema.registrar_venta(self.venta_actual, sucursal, total)
        if exito:
            if tk.messagebox.askyesno("Generar Recibo", f"Venta {venta_id} registrada.\n¿Desea generar un recibo en PDF?"):
                archivo, msg = self.sistema.generar_recibo_venta_pdf(venta_id)
                if archivo: self.mostrar_toast("Recibo Generado", msg, 'info'); webbrowser.open(archivo)
                else: Messagebox.show_error(msg, "Error")
            if productos_bajos:
                for p in productos_bajos: self.mostrar_toast("Alerta de Stock Bajo", f"SKU: {p['sku']} - Stock: {p['stock']}", 'warning')
            self.venta_actual = []; self.actualizar_carrito_gui(); self.actualizar_todo()
        else: Messagebox.showerror("No se pudo completar la venta por falta de stock.", "Error de Venta")

    def crear_pestaña_transferencias(self):
        frame = ttk.Frame(self.notebook, padding=(10)); self.notebook.add(frame, text='🔄 Transferencias')
        lframe = ttk.LabelFrame(frame, text="Mover Stock entre Sucursales", padding=(15)); lframe.pack(fill='x', pady=10)
        ttk.Label(lframe, text="SKU:").grid(row=0, column=0, padx=5, pady=5, sticky='w'); self.transfer_sku = ttk.Entry(lframe); self.transfer_sku.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(lframe, text="Cantidad:").grid(row=1, column=0, padx=5, pady=5, sticky='w'); self.transfer_cantidad = ttk.Entry(lframe); self.transfer_cantidad.grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(lframe, text="Origen:").grid(row=2, column=0, padx=5, pady=5, sticky='w'); self.transfer_origen = ttk.Combobox(lframe, state="readonly"); self.transfer_origen.grid(row=2, column=1, padx=5, pady=5)
        ttk.Label(lframe, text="Destino:").grid(row=3, column=0, padx=5, pady=5, sticky='w'); self.transfer_destino = ttk.Combobox(lframe, state="readonly"); self.transfer_destino.grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(lframe, text="Realizar Transferencia", command=self.realizar_transferencia_gui, bootstyle="info").grid(row=4, column=0, columnspan=2, pady=10)
    
    def realizar_transferencia_gui(self):
        sku = self.transfer_sku.get(); origen = self.transfer_origen.get(); destino = self.transfer_destino.get()
        try: cantidad = int(self.transfer_cantidad.get())
        except ValueError: Messagebox.showerror("La cantidad debe ser un número.", "Error"); return
        if not all([sku, origen, destino]) or cantidad <= 0: Messagebox.showerror("Todos los campos son obligatorios.", "Error"); return
        if origen == destino: Messagebox.showerror("Origen y destino no pueden ser iguales.", "Error"); return
        exito, mensaje = self.sistema.transferir_productos(sku, cantidad, origen, destino)
        if exito:
            self.mostrar_toast("Éxito", mensaje, "success"); self.actualizar_todo()
        else: Messagebox.show_error(mensaje, "Error de Transferencia")
            
    def crear_pestaña_sistema(self):
        frame = ttk.Frame(self.notebook, padding=(10)); self.notebook.add(frame, text='⚙️ Sistema')
        carga_frame = ttk.LabelFrame(frame, text="Carga Masiva de Datos", padding=15); carga_frame.pack(fill='x', pady=10)
        ttk.Button(carga_frame, text="Cargar/Actualizar Inventario desde CSV", command=self.cargar_csv_gui, bootstyle="success").pack(pady=10)
        danger_frame = ttk.LabelFrame(frame, text="Zona Peligrosa", padding=15, bootstyle="danger"); danger_frame.pack(fill='x', pady=10)
        ttk.Button(danger_frame, text="REINICIALIZAR SISTEMA (ELIMINAR TODO)", command=self.confirmar_reinicio_gui, bootstyle="danger").pack(pady=10)
    
    def cargar_csv_gui(self):
        path = filedialog.askopenfilename(title="Seleccionar archivo CSV", initialdir="data", filetypes=[("CSV Files", "*.csv")])
        if not path: return
        exito, mensaje = self.sistema.procesar_carga_csv(path)
        if exito:
            self.mostrar_toast("Éxito", mensaje, "success"); self.actualizar_todo()
        else: Messagebox.show_error(mensaje, "Error al cargar CSV")

    def confirmar_reinicio_gui(self):
        dialog = ttk.dialogs.dialogs.QueryDialog(parent=self.root, title="Confirmación de Reinicio Total", prompt="Esta acción es irreversible.\n\nPara confirmar, escriba:\nsi, seguro de eliminar todo", initialvalue="")
        dialog.show()
        if dialog.result == "si, seguro de eliminar todo":
            exito, mensaje = self.sistema.reinicializar_sistema()
            if exito: self.mostrar_toast("Sistema Reiniciado", mensaje, "danger"); self.actualizar_todo()
        elif dialog.result is not None:
            Messagebox.show_warning("La frase no coincide. Acción cancelada.", "Confirmación Fallida")

    def mostrar_toast(self, titulo, mensaje, bootstyle='default', duration=5000):
        root_x=self.root.winfo_x(); root_y=self.root.winfo_y(); root_width=self.root.winfo_width(); root_height=self.root.winfo_height()
        toast_width=300; toast_height=75
        pos_x = root_x + (root_width // 2) - (toast_width // 2); pos_y = root_y + (root_height // 2) - (toast_height // 2)
        ToastNotification(title=titulo, message=mensaje, duration=duration, bootstyle=bootstyle, position=(pos_x, pos_y, 'nw')).show_toast()
        
    def actualizar_todo(self):
        """Método central para refrescar toda la UI después de un cambio de datos."""
        self.actualizar_filtros_sucursal()
        self.actualizar_lista_productos()
        self.actualizar_dashboard()
        self.limpiar_formulario()

# --- Punto de Entrada de la Aplicación ---
if __name__ == "__main__":
    root = ttk.Window(themename="superhero")
    app = App(root)
    root.mainloop()

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import data_handler as dh

# Page configuration
st.set_page_config(
    page_title="IROH - Bitácora de Robots",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium looks and glassmorphism elements
st.markdown("""
<style>
    /* Styling headers */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
    }
    
    /* Premium custom status badges */
    .badge {
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
    }
    .badge-ok {
        background-color: rgba(46, 204, 113, 0.2);
        color: #2ecc71;
        border: 1px solid #2ecc71;
    }
    .badge-atencion {
        background-color: rgba(241, 196, 15, 0.2);
        color: #f1c40f;
        border: 1px solid #f1c40f;
    }
    .badge-falla {
        background-color: rgba(231, 76, 60, 0.2);
        color: #e74c3c;
        border: 1px solid #e74c3c;
    }
    .badge-dead {
        background-color: rgba(149, 165, 166, 0.2);
        color: #95a5a6;
        border: 1px solid #95a5a6;
    }
    .badge-empty {
        background-color: rgba(255, 255, 255, 0.1);
        color: #888888;
        border: 1px solid #888888;
    }
</style>
""", unsafe_allow_html=True)

# Main Title and Sede Badge
col_header_title, col_header_badge = st.columns([8, 2])
with col_header_title:
    st.title("🤖 IROH - Bitácora & Mantenimiento de Robots")
    st.write("Panel inteligente para el control de inventario y mantención técnica.")
with col_header_badge:
    st.write("")
    st.markdown('<span class="badge badge-ok" style="font-size:14px; padding:8px 16px;">📍 Sede Curicó</span>', unsafe_allow_html=True)

# Check if the Excel file is available
if not dh.check_file_exists():
    st.error(f"❌ No se encontró el archivo Excel de la bitácora en la ruta: `{dh.get_excel_path()}`")
    st.info("Por favor, asegúrate de que el archivo `BitacoraCurico (1).xlsx` esté en tu carpeta de Descargas.")
    st.stop()

@st.cache_data(ttl=15)
def load_all_data_cached():
    data = dh.load_data()
    df_rob_statuses = dh.get_robot_statuses()
    return data, df_rob_statuses

# Load data
try:
    data, df_rob_statuses = load_all_data_cached()
    df_inv = data['inventario']
    df_rob = data['robots']
    df_reg = data['registro_clean']
except Exception as e:
    st.error("Error al conectar con Google Sheets:")
    st.exception(e)
    
    # Panel de depuración para ver qué se está cargando en los Secrets
    st.markdown("---")
    st.markdown("### 🔍 Panel de Diagnóstico de Credenciales")
    st.write("Claves detectadas en `st.secrets`:", list(st.secrets.keys()))
    if "gcp_service_account" in st.secrets:
        val = st.secrets["gcp_service_account"]
        st.write("Tipo de dato de `gcp_service_account`:", type(val).__name__)
        if isinstance(val, str):
            st.write("Longitud de la cadena de texto:", len(val))
            try:
                import json
                d = json.loads(val)
                st.write("✅ El JSON se pudo decodificar correctamente.")
                st.write("Claves dentro del JSON:", list(d.keys()))
                if "private_key" in d:
                    pk = d["private_key"]
                    st.write(f"Longitud de `private_key` en JSON: {len(pk)} caracteres.")
                    st.write(f"Saltos de línea reales (\\n): {pk.count('\n')}")
                    st.write(f"Retornos de carro reales (\\r): {pk.count('\r')}")
                    st.write(f"Textos '\\n' literales: {pk.count('\\\\n')}")
            except Exception as json_e:
                st.error(f"❌ Error al decodificar como JSON: {json_e}")
                st.text("Contenido recibido (primeros 100 caracteres):")
                st.code(val[:100])
        elif hasattr(val, "keys"):
            st.write("Claves dentro de la tabla TOML:", list(val.keys()))
            if "private_key" in val:
                pk = val["private_key"]
                st.write(f"Longitud de `private_key` en TOML: {len(pk)} caracteres.")
                st.write(f"Saltos de línea reales (\\n): {pk.count('\n')}")
                st.write(f"Retornos de carro reales (\\r): {pk.count('\r')}")
                st.write(f"Textos '\\n' literales: {pk.count('\\\\n')}")
    else:
        st.warning("⚠️ No se encontró la clave `gcp_service_account` en `st.secrets`.")
    st.stop()

# Sidebar Setup
with st.sidebar:
    st.image("https://img.icons8.com/nolan/128/robot.png", width=80)
    st.subheader("Configuración")
    st.info("🔄 Conectado a: \nGoogle Sheets (Nube)")
    
    encargado_predeterminado = st.text_input("Encargado de Mantención:", value="Vicente Guerra")
    
    st.write("---")
    st.markdown("### Resumen de la Sede")
    total_robots = len(df_rob)
    st.metric("Total Robots", total_robots)
    
    # Calculate status counts
    state_counts = df_rob_statuses['Estado'].value_counts()
    ok_count = state_counts.get('OK', 0)
    atencion_count = state_counts.get('Atención', 0)
    falla_count = state_counts.get('Falla', 0)
    out_count = state_counts.get('Fuera de servicio', 0)
    no_reg_count = state_counts.get('Sin Registro', 0)

# Create Main App Tabs
tab_dash, tab_robots, tab_inv, tab_reg = st.tabs([
    "📊 Dashboard", 
    "🤖 Robots & Historial", 
    "📦 Inventario", 
    "📝 Registrar Mantención"
])

# ----------------- TAB 1: DASHBOARD -----------------
with tab_dash:
    st.header("Resumen del Estado de la Flota")
    
    # Grid of metrics cards
    col_ok, col_atencion, col_falla, col_fuera, col_sin = st.columns(5)
    
    with col_ok:
        st.markdown(
            f"""
            <div style="background-color:#1e2a22; border:1px solid #2ecc71; border-radius:10px; padding:15px; text-align:center;">
                <h4 style="color:#2ecc71; margin:0;">🟢 En Servicio (OK)</h4>
                <p style="font-size:32px; font-weight:bold; color:white; margin:10px 0 0 0;">{ok_count}</p>
            </div>
            """, unsafe_allow_html=True
        )
    with col_atencion:
        st.markdown(
            f"""
            <div style="background-color:#2a2618; border:1px solid #f1c40f; border-radius:10px; padding:15px; text-align:center;">
                <h4 style="color:#f1c40f; margin:0;">🟡 En Atención</h4>
                <p style="font-size:32px; font-weight:bold; color:white; margin:10px 0 0 0;">{atencion_count}</p>
            </div>
            """, unsafe_allow_html=True
        )
    with col_falla:
        st.markdown(
            f"""
            <div style="background-color:#2e1f1e; border:1px solid #e74c3c; border-radius:10px; padding:15px; text-align:center;">
                <h4 style="color:#e74c3c; margin:0;">🔴 Con Falla</h4>
                <p style="font-size:32px; font-weight:bold; color:white; margin:10px 0 0 0;">{falla_count}</p>
            </div>
            """, unsafe_allow_html=True
        )
    with col_fuera:
        st.markdown(
            f"""
            <div style="background-color:#22252a; border:1px solid #95a5a6; border-radius:10px; padding:15px; text-align:center;">
                <h4 style="color:#95a5a6; margin:0;">⚫ Fuera de Servicio</h4>
                <p style="font-size:32px; font-weight:bold; color:white; margin:10px 0 0 0;">{out_count}</p>
            </div>
            """, unsafe_allow_html=True
        )
    with col_sin:
        st.markdown(
            f"""
            <div style="background-color:#1c1e22; border:1px solid #888888; border-radius:10px; padding:15px; text-align:center;">
                <h4 style="color:#888888; margin:0;">⚪ Sin Registro</h4>
                <p style="font-size:32px; font-weight:bold; color:white; margin:10px 0 0 0;">{no_reg_count}</p>
            </div>
            """, unsafe_allow_html=True
        )

    st.write("")
    
    # Second Row: Charts
    col_chart1, col_chart2 = st.columns([4, 6])
    
    with col_chart1:
        st.subheader("Estado de la Flota")
        
        # Prepare fleet data for charting
        fleet_status_data = pd.DataFrame({
            "Estado": ["OK", "Atención", "Falla", "Fuera de servicio", "Sin Registro"],
            "Cantidad": [ok_count, atencion_count, falla_count, out_count, no_reg_count]
        })
        
        chart_fleet = alt.Chart(fleet_status_data).mark_bar().encode(
            x=alt.X("Cantidad:Q", title="Número de Robots"),
            y=alt.Y("Estado:N", sort="-x", title=""),
            color=alt.Color("Estado:N", scale=alt.Scale(
                domain=["OK", "Atención", "Falla", "Fuera de servicio", "Sin Registro"],
                range=["#2ecc71", "#f1c40f", "#e74c3c", "#95a5a6", "#888888"]
            ), legend=None)
        ).properties(height=250)
        
        st.altair_chart(chart_fleet, use_container_width=True)

    with col_chart2:
        st.subheader("Alertas de Repuestos & Stock Crítico")
        
        # Show items with low stock (e.g. Stock <= 2 and we have some total entries)
        low_stock_threshold = 2
        
        # Filter for items that actually are components (have entries)
        df_inv_numeric = df_inv.copy()
        df_inv_numeric['Entradas Num'] = pd.to_numeric(df_inv_numeric['Entradas (total)'], errors='coerce').fillna(0)
        df_inv_components = df_inv_numeric[df_inv_numeric['Entradas Num'] > 0]
        
        # Find low stock items
        df_low_stock = df_inv_components[df_inv_components['Stock Calculado'] <= low_stock_threshold].copy()
        
        if not df_low_stock.empty:
            st.warning(f"⚠️ ¡Atención! Tienes {len(df_low_stock)} componentes con stock crítico (menos de {low_stock_threshold + 1} unidades):")
            
            # Simple chart of low stock items
            chart_stock = alt.Chart(df_low_stock).mark_bar(color="#e74c3c").encode(
                x=alt.X("Stock Calculado:Q", title="Stock Restante", axis=alt.Axis(tickMinStep=1)),
                y=alt.Y("Nombre del Material:N", sort="x", title="")
            ).properties(height=250)
            
            st.altair_chart(chart_stock, use_container_width=True)
        else:
            st.success("✅ ¡Todo bien con el inventario! No hay componentes con stock crítico.")
            # Show a chart of the top 8 items with the most stock
            df_top_stock = df_inv_components.sort_values(by='Stock Calculado', ascending=False).head(8)
            chart_stock = alt.Chart(df_top_stock).mark_bar(color="#2ecc71").encode(
                x=alt.X("Stock Calculado:Q", title="Stock Actual"),
                y=alt.Y("Nombre del Material:N", sort="-x", title="")
            ).properties(height=250)
            st.altair_chart(chart_stock, use_container_width=True)

# ----------------- TAB 2: ROBOTS & HISTORIAL -----------------
with tab_robots:
    st.header("Directorio de Robots y Diagnósticos")
    
    # Search filter
    search_query = st.text_input("🔍 Buscar robot por ID, Nombre del Grupo o Comentario:", "")
    
    # Filter the statuses DataFrame
    filtered_robots = df_rob_statuses.copy()
    if search_query:
        query = search_query.lower()
        filtered_robots = filtered_robots[
            filtered_robots['ID Robot'].str.lower().str.contains(query) |
            filtered_robots['Nombre del Grupo'].str.lower().str.contains(query) |
            filtered_robots['Estado'].str.lower().str.contains(query) |
            filtered_robots['Último Comentario'].str.lower().str.contains(query) |
            filtered_robots['Observaciones Fijas'].str.lower().str.contains(query)
        ]

    st.write(f"Mostrando {len(filtered_robots)} de {len(df_rob_statuses)} robots:")

    # Display robots in expanders (better for mobile screen sizes)
    for _, robot in filtered_robots.iterrows():
        r_id = robot['ID Robot']
        r_name = robot['Nombre del Grupo']
        r_state = robot['Estado']
        r_comment = robot['Último Comentario']
        r_loc = robot['Ubicación']
        r_obs = robot['Observaciones Fijas']
        
        # Color indicator based on state
        state_emoji = "⚪"
        badge_class = "badge-empty"
        if r_state == "OK":
            state_emoji = "🟢"
            badge_class = "badge-ok"
        elif r_state == "Atención":
            state_emoji = "🟡"
            badge_class = "badge-atencion"
        elif r_state == "Falla":
            state_emoji = "🔴"
            badge_class = "badge-falla"
        elif r_state == "Fuera de servicio":
            state_emoji = "⚫"
            badge_class = "badge-dead"
            
        header_text = f"{state_emoji} {r_id} — {r_name} ({r_loc})"
        
        with st.expander(header_text):
            col_rob_info, col_rob_hist = st.columns([4, 6])
            
            with col_rob_info:
                st.markdown(f"**Estado Actual:** <span class='badge {badge_class}'>{r_state}</span>", unsafe_allow_html=True)
                st.markdown(f"**Ubicación:** {r_loc}")
                
                if r_obs:
                    st.markdown(f"**Observaciones Fijas (Robots):** *{r_obs}*")
                
                st.write("---")
                st.write("**Último diagnóstico registrado:**")
                if r_comment:
                    st.info(f"\"{r_comment}\"")
                else:
                    st.write("*Sin diagnósticos registrados aún.*")
                    
            with col_rob_hist:
                st.write("📋 **Historial de Mantención (Últimas semanas):**")
                # Load history from preloaded df_reg in memory (avoids N+1 Google API calls)
                r_hist = df_reg[df_reg['Robot'] == r_id].copy().sort_values(by='Semana')
                if not r_hist.empty:
                    # Clean display of history
                    display_cols = ['Semana', 'Fecha', 'Estado', 'Encargado', 'Descripción / Falla', 'Repuesto Usado', 'Cant.']
                    display_df = r_hist[display_cols].copy()
                    display_df['Fecha'] = display_df['Fecha'].astype(str)
                    st.dataframe(
                        display_df.sort_values(by='Semana', ascending=False),
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.write("*No hay logs registrados para este robot en el historial.*")

# ----------------- TAB 3: INVENTARIO -----------------
with tab_inv:
    st.header("Inventario de Componentes y Materiales")
    
    st.write("💡 *El stock actual se calcula restando dinámicamente los repuestos consumidos en la hoja Registro.*")
    
    # Material filter
    search_inv = st.text_input("🔍 Filtrar material por nombre:", "")
    
    # Filter DataFrame
    filtered_inv = df_inv.copy()
    if search_inv:
        filtered_inv = filtered_inv[filtered_inv['Nombre del Material'].str.lower().str.contains(search_inv.lower())]

    # Style table view
    def highlight_stock(row):
        stock = row['Stock Calculado']
        entradas = pd.to_numeric(row['Entradas (total)'], errors='coerce')
        
        if pd.isna(entradas) or entradas == 0:
            return [''] * len(row) # Skip non-numeric or non-material rows like dividers
        
        if stock == 0:
            return ['background-color: rgba(231, 76, 60, 0.15); color: #e74c3c; font-weight: bold'] * len(row)
        elif stock <= 2:
            return ['background-color: rgba(241, 196, 15, 0.15); color: #f1c40f; font-weight: bold'] * len(row)
        else:
            return [''] * len(row)

    styled_inv = filtered_inv[['Nombre del Material', 'Entradas (total)', 'Stock Calculado', 'Comentarios']].copy()
    styled_inv['Entradas (total)'] = styled_inv['Entradas (total)'].astype(str)
    
    # Display table
    st.dataframe(
        styled_inv.style.apply(highlight_stock, axis=1),
        hide_index=True,
        use_container_width=True,
        height=600
    )

# ----------------- TAB 4: REGISTRAR MANTENCIÓN -----------------
with tab_reg:
    st.header("Registro de Mantenimiento Semanal")
    st.write("Llena este formulario para actualizar el estado del robot e inventario en la bitácora.")
    
    # Get active robots list for select box
    robots_list = [f"{r['ID Robot']} - {r['Nombre del Grupo']}" for _, r in df_rob.iterrows()]
    
    # Get parts list from inventory for select box
    parts_list = ["Ninguno"] + sorted(df_inv['Nombre del Material'].dropna().unique().tolist())
    
    # Create the Form
    with st.form("maintenance_form", clear_on_submit=False):
        col_form1, col_form2 = st.columns(2)
        
        with col_form1:
            # 1. Week selection
            # Standard list of weeks in template
            weeks = ["Sem 01", "Sem 02", "Sem 03", "Sem 04", "Sem 05", "Sem 06", "Sem 07", "Sem 08"]
            selected_week = st.selectbox("Seleccionar Semana:", weeks, index=2) # Default Sem 03 as it is the first empty template week
            
            # 2. Robot selection
            selected_robot_str = st.selectbox("Robot a Intervenir:", robots_list)
            selected_robot_id = selected_robot_str.split(" - ")[0]
            
            # 3. Status selection
            estado_options = ["OK", "Atención", "Falla"]
            selected_estado = st.radio("Estado del Robot:", estado_options, horizontal=True, index=0)
            
            # 4. Encargado
            encargado_val = st.text_input("Encargado:", value=encargado_predeterminado)
            
        with col_form2:
            # 5. Comment / description of issue
            desc_val = st.text_area("Descripción del Mantenimiento / Falla:", placeholder="Escribe el diagnóstico del robot y el trabajo realizado...")
            
            # 6. Part used
            selected_part = st.selectbox("Repuesto Utilizado (opcional):", parts_list)
            
            # 7. Quantity used
            col_qty, col_stock_info = st.columns(2)
            with col_qty:
                qty_val = st.number_input("Cantidad de Repuestos Usados:", min_value=0, max_value=50, value=0, step=1)
                
            with col_stock_info:
                # Show current stock of the selected part
                if selected_part != "Ninguno":
                    current_stock = df_inv[df_inv['Nombre del Material'] == selected_part]['Stock Calculado'].values
                    if len(current_stock) > 0:
                        st.markdown(f"<br>**Stock disponible de '{selected_part}':** `{int(current_stock[0])}` unidades", unsafe_allow_html=True)
                    else:
                        st.markdown("<br>**Stock disponible:** `No definido`", unsafe_allow_html=True)
                else:
                    st.markdown("<br>**No se consumirá ningún repuesto del stock.**", unsafe_allow_html=True)
                    
        # Submit button
        submit_btn = st.form_submit_button("💾 Guardar Mantenimiento en Bitácora", use_container_width=True)
        
        if submit_btn:
            # Basic validation
            if not encargado_val:
                st.error("❌ El nombre del Encargado es obligatorio.")
            elif not desc_val:
                st.error("❌ Debes ingresar una descripción o falla para registrar la actividad.")
            elif selected_part != "Ninguno" and qty_val <= 0:
                st.error(f"❌ Si seleccionaste un repuesto ({selected_part}), debes ingresar una cantidad mayor a 0.")
            elif selected_part == "Ninguno" and qty_val > 0:
                st.error("❌ Si ingresaste una cantidad de repuestos, debes seleccionar el material correspondiente en la lista.")
            else:
                # Check stock availability
                stock_ok = True
                if selected_part != "Ninguno":
                    curr_stock_val = df_inv[df_inv['Nombre del Material'] == selected_part]['Stock Calculado'].values
                    if len(curr_stock_val) > 0 and curr_stock_val[0] < qty_val:
                        st.error(f"❌ Stock insuficiente. Solo quedan `{int(curr_stock_val[0])}` de `{selected_part}` disponibles.")
                        stock_ok = False
                
                if stock_ok:
                    with st.spinner("Guardando en Google Sheets..."):
                        # Save
                        success = dh.save_maintenance(
                            semana=selected_week,
                            robot_id=selected_robot_id,
                            estado=selected_estado,
                            encargado=encargado_val,
                            descripcion=desc_val,
                            repuesto=selected_part,
                            cantidad=qty_val
                        )
                        if success:
                            st.cache_data.clear() # Clear the cache to load fresh data on rerun
                            st.success(f"✅ ¡Registro guardado exitosamente para el robot **{selected_robot_id}** en la **{selected_week}**!")
                            st.balloons()
                            # Rerun to refresh all data tables and calculations in the UI
                            st.rerun()

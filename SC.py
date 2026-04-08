"""
============================================================================
SISTEMA DE CORRESPONDENCIA - IMPLEMENTACIÓN EN STREAMLIT
============================================================================
Modernización del sistema de correspondencia de Delphi a Python + Streamlit
Incluye gestión de recepción y despacho de documentos
============================================================================
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
import io

# ============================================================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================================================

st.set_page_config(
    page_title="Sistema de Correspondencia",
    page_icon="📨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# FUNCIONES DE BASE DE DATOS
# ============================================================================

def init_database():
    """Inicializa la base de datos SQLite con las tablas necesarias"""
    conn = sqlite3.connect('correspondencia.db')
    cursor = conn.cursor()
    
    # Tabla de Recepción de Documentos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recepcion_documentos (
            id_recepcion INTEGER PRIMARY KEY AUTOINCREMENT,
            via_documento TEXT,
            nom_remitente TEXT NOT NULL,
            nom_localidad TEXT,
            num_oficio TEXT NOT NULL,
            nom_subclasificacion TEXT,
            fecha_documento DATE NOT NULL,
            fecha_recepcion DATE NOT NULL,
            hora_recepcion TIME,
            plazo_respuesta INTEGER,
            fecha_vcto DATE,
            dias_entrega INTEGER,
            materia TEXT,
            nombre_responsable TEXT,
            referencia TEXT,
            fecha_digitacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            rut TEXT,
            nombre_ingresado_por TEXT,
            estado TEXT DEFAULT 'Pendiente'
        )
    ''')
    
    # Tabla de Despacho
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS despacho_documentos (
            id_despacho INTEGER PRIMARY KEY AUTOINCREMENT,
            via_documento TEXT,
            nom_remitente TEXT NOT NULL,
            atencion TEXT,
            num_oficio_interno TEXT,
            fecha_documento DATE NOT NULL,
            materia TEXT,
            nom_localidad TEXT,
            num_oficio TEXT NOT NULL,
            rut TEXT,
            fecha_digitacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            nombre_ingresado_por TEXT,
            estado TEXT DEFAULT 'Enviado'
        )
    ''')
    
    # Tabla de Adjuntos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recepcion_adjuntos (
            id_adjunto INTEGER PRIMARY KEY AUTOINCREMENT,
            id_recepcion INTEGER,
            nombre_archivo TEXT,
            ruta_archivo TEXT,
            fecha_adjunto DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_recepcion) REFERENCES recepcion_documentos(id_recepcion)
        )
    ''')
    
    # Tabla de Remitentes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS remitentes (
            id_remitente INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_remitente TEXT NOT NULL UNIQUE,
            rut TEXT,
            direccion TEXT,
            telefono TEXT,
            email TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def insertar_documento_recepcion(datos):
    """Inserta un nuevo documento de recepción"""
    conn = sqlite3.connect('correspondencia.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO recepcion_documentos (
            via_documento, nom_remitente, nom_localidad, num_oficio,
            nom_subclasificacion, fecha_documento, fecha_recepcion,
            hora_recepcion, plazo_respuesta, fecha_vcto, materia,
            nombre_responsable, referencia, nombre_ingresado_por, estado
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', datos)
    
    conn.commit()
    doc_id = cursor.lastrowid
    conn.close()
    return doc_id

def actualizar_documento_recepcion(doc_id, datos):
    """Actualiza un documento de recepción existente"""
    conn = sqlite3.connect('correspondencia.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE recepcion_documentos
        SET via_documento = ?, nom_remitente = ?, nom_localidad = ?,
            num_oficio = ?, nom_subclasificacion = ?, fecha_documento = ?,
            materia = ?, nombre_responsable = ?, referencia = ?, estado = ?
        WHERE id_recepcion = ?
    ''', (*datos, doc_id))
    
    conn.commit()
    conn.close()

def eliminar_documento_recepcion(doc_id):
    """Elimina un documento de recepción"""
    conn = sqlite3.connect('correspondencia.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM recepcion_documentos WHERE id_recepcion = ?', (doc_id,))
    conn.commit()
    conn.close()

def buscar_documentos_recepcion(filtros):
    """Busca documentos de recepción con filtros"""
    conn = sqlite3.connect('correspondencia.db')
    
    query = "SELECT * FROM recepcion_documentos WHERE 1=1"
    params = []
    
    if filtros.get('remitente'):
        query += " AND nom_remitente LIKE ?"
        params.append(f"%{filtros['remitente']}%")
    
    if filtros.get('oficio'):
        query += " AND num_oficio LIKE ?"
        params.append(f"%{filtros['oficio']}%")
    
    if filtros.get('fecha_desde'):
        query += " AND fecha_documento >= ?"
        params.append(filtros['fecha_desde'])
    
    if filtros.get('fecha_hasta'):
        query += " AND fecha_documento <= ?"
        params.append(filtros['fecha_hasta'])
    
    if filtros.get('estado'):
        query += " AND estado = ?"
        params.append(filtros['estado'])
    
    query += " ORDER BY fecha_recepcion DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def obtener_alertas_vencimiento():
    """Obtiene documentos próximos a vencer o vencidos"""
    conn = sqlite3.connect('correspondencia.db')
    query = '''
        SELECT id_recepcion, nom_remitente, num_oficio, fecha_documento,
               fecha_vcto, materia, nombre_responsable, referencia
        FROM recepcion_documentos
        WHERE fecha_vcto IS NOT NULL 
        AND fecha_vcto <= date('now', '+7 days')
        AND estado != 'Finalizado'
        ORDER BY fecha_vcto ASC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def obtener_estadisticas():
    """Obtiene estadísticas del sistema"""
    conn = sqlite3.connect('correspondencia.db')
    
    stats = {}
    
    # Total de documentos
    stats['total_recepcion'] = pd.read_sql_query(
        "SELECT COUNT(*) as total FROM recepcion_documentos", conn
    )['total'][0]
    
    stats['total_despacho'] = pd.read_sql_query(
        "SELECT COUNT(*) as total FROM despacho_documentos", conn
    )['total'][0]
    
    # Pendientes
    stats['pendientes'] = pd.read_sql_query(
        "SELECT COUNT(*) as total FROM recepcion_documentos WHERE estado = 'Pendiente'", conn
    )['total'][0]
    
    # Vencidos
    stats['vencidos'] = pd.read_sql_query(
        "SELECT COUNT(*) as total FROM recepcion_documentos WHERE fecha_vcto < date('now') AND estado != 'Finalizado'", conn
    )['total'][0]
    
    # Por remitente (top 10)
    stats['por_remitente'] = pd.read_sql_query('''
        SELECT nom_remitente, COUNT(*) as cantidad
        FROM recepcion_documentos
        GROUP BY nom_remitente
        ORDER BY cantidad DESC
        LIMIT 10
    ''', conn)
    
    conn.close()
    return stats

# ============================================================================
# INTERFAZ DE USUARIO
# ============================================================================

def main():
    """Función principal de la aplicación"""
    
    # Inicializar base de datos
    init_database()
    
    # Título principal
    st.title("📨 Sistema de Correspondencia")
    st.markdown("---")
    
    # Barra lateral - Menú
    with st.sidebar:
        st.image("https://via.placeholder.com/200x80/6B46C1/FFFFFF?text=CORRESPONDENCIA", use_container_width=True)
        st.markdown("### Menú Principal")
        
        menu = st.radio(
            "Seleccione una opción:",
            ["🏠 Dashboard", "📥 Recepción", "📤 Despacho", "🔍 Búsqueda", 
             "⚠️ Alertas", "📊 Estadísticas", "⚙️ Configuración"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown(f"**Usuario:** {st.session_state.get('usuario', 'Admin')}")
        st.markdown(f"**Fecha:** {date.today().strftime('%d/%m/%Y')}")
    
    # Contenido principal según el menú seleccionado
    if menu == "🏠 Dashboard":
        mostrar_dashboard()
    elif menu == "📥 Recepción":
        gestionar_recepcion()
    elif menu == "📤 Despacho":
        gestionar_despacho()
    elif menu == "🔍 Búsqueda":
        busqueda_avanzada()
    elif menu == "⚠️ Alertas":
        mostrar_alertas()
    elif menu == "📊 Estadísticas":
        mostrar_estadisticas()
    elif menu == "⚙️ Configuración":
        configuracion()

def mostrar_dashboard():
    """Muestra el panel de control principal"""
    st.header("📊 Dashboard")
    
    stats = obtener_estadisticas()
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📥 Total Recepción", stats['total_recepcion'])
    with col2:
        st.metric("📤 Total Despacho", stats['total_despacho'])
    with col3:
        st.metric("⏳ Pendientes", stats['pendientes'], delta=None)
    with col4:
        st.metric("⚠️ Vencidos", stats['vencidos'], delta=-stats['vencidos'] if stats['vencidos'] > 0 else 0)
    
    st.markdown("---")
    
    # Alertas recientes
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("📋 Documentos Recientes")
        conn = sqlite3.connect('correspondencia.db')
        df_recientes = pd.read_sql_query('''
            SELECT id_recepcion as ID, nom_remitente as Remitente, 
                   num_oficio as Oficio, fecha_recepcion as "Fecha Recepción",
                   estado as Estado
            FROM recepcion_documentos
            ORDER BY fecha_recepcion DESC
            LIMIT 10
        ''', conn)
        conn.close()
        
        if not df_recientes.empty:
            st.dataframe(df_recientes, use_container_width=True, hide_index=True)
        else:
            st.info("No hay documentos registrados")
    
    with col_right:
        st.subheader("📈 Top Remitentes")
        if not stats['por_remitente'].empty:
            st.bar_chart(stats['por_remitente'].set_index('nom_remitente')['cantidad'])
        else:
            st.info("No hay datos disponibles")

def gestionar_recepcion():
    """Gestiona la recepción de documentos"""
    st.header("📥 Gestión de Recepción de Documentos")
    
    tab1, tab2, tab3 = st.tabs(["➕ Nuevo Documento", "📝 Editar", "📋 Listar"])
    
    with tab1:
        with st.form("form_nuevo_documento"):
            st.subheader("Registrar Nuevo Documento")
            
            col1, col2 = st.columns(2)
            
            with col1:
                via_doc = st.selectbox("Vía Documento", 
                    ["Correo Electrónico", "Oficio Físico", "Fax", "Carta Certificada", "Otro"])
                remitente = st.text_input("Remitente *", placeholder="Nombre del remitente")
                localidad = st.text_input("Localidad", placeholder="Ciudad/Comuna")
                num_oficio = st.text_input("Número Oficio *", placeholder="Ej: OF-2024-001")
                subclasificacion = st.selectbox("Subclasificación",
                    ["Urgente", "Normal", "Reservado", "Confidencial"])
                fecha_doc = st.date_input("Fecha Documento *", value=date.today())
                fecha_recep = st.date_input("Fecha Recepción *", value=date.today())
            
            with col2:
                hora_recep = st.time_input("Hora Recepción")
                plazo = st.number_input("Plazo Respuesta (días)", min_value=0, value=10)
                
                if plazo > 0:
                    fecha_vcto = fecha_recep + timedelta(days=plazo)
                    st.date_input("Fecha Vencimiento", value=fecha_vcto, disabled=True)
                
                responsable = st.text_input("Responsable", placeholder="Nombre del responsable")
                referencia = st.text_input("Referencia", placeholder="Referencia del documento")
                estado = st.selectbox("Estado", ["Pendiente", "En Proceso", "Finalizado"])
            
            materia = st.text_area("Materia/Asunto", placeholder="Descripción del asunto del documento")
            
            submitted = st.form_submit_button("💾 Guardar Documento", use_container_width=True)
            
            if submitted:
                if not remitente or not num_oficio:
                    st.error("⚠️ Los campos Remitente y Número de Oficio son obligatorios")
                else:
                    try:
                        fecha_vcto_calc = fecha_recep + timedelta(days=plazo) if plazo > 0 else None
                        
                        datos = (
                            via_doc, remitente, localidad, num_oficio, subclasificacion,
                            fecha_doc, fecha_recep, hora_recep, plazo, fecha_vcto_calc,
                            materia, responsable, referencia, 
                            st.session_state.get('usuario', 'Admin'), estado
                        )
                        
                        doc_id = insertar_documento_recepcion(datos)
                        st.success(f"✅ Documento guardado exitosamente con ID: {doc_id}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al guardar: {str(e)}")
    
    with tab2:
        st.subheader("Editar Documento Existente")
        
        # Buscar documento por ID
        doc_id = st.number_input("ID del Documento", min_value=1, step=1)
        
        if st.button("🔍 Buscar Documento"):
            conn = sqlite3.connect('correspondencia.db')
            df = pd.read_sql_query(
                "SELECT * FROM recepcion_documentos WHERE id_recepcion = ?",
                conn, params=(doc_id,)
            )
            conn.close()
            
            if not df.empty:
                st.session_state['doc_editar'] = df.iloc[0].to_dict()
                st.success("Documento encontrado")
            else:
                st.error("Documento no encontrado")
        
        if 'doc_editar' in st.session_state:
            doc = st.session_state['doc_editar']
            
            with st.form("form_editar_documento"):
                col1, col2 = st.columns(2)
                
                with col1:
                    via_doc = st.text_input("Vía Documento", value=doc.get('via_documento', ''))
                    remitente = st.text_input("Remitente", value=doc.get('nom_remitente', ''))
                    localidad = st.text_input("Localidad", value=doc.get('nom_localidad', ''))
                    num_oficio = st.text_input("Número Oficio", value=doc.get('num_oficio', ''))
                    subclasif = st.text_input("Subclasificación", value=doc.get('nom_subclasificacion', ''))
                
                with col2:
                    fecha_doc = st.date_input("Fecha Documento", 
                        value=datetime.strptime(doc['fecha_documento'], '%Y-%m-%d').date() 
                        if doc.get('fecha_documento') else date.today())
                    responsable = st.text_input("Responsable", value=doc.get('nombre_responsable', ''))
                    referencia = st.text_input("Referencia", value=doc.get('referencia', ''))
                    estado = st.selectbox("Estado", 
                        ["Pendiente", "En Proceso", "Finalizado"],
                        index=["Pendiente", "En Proceso", "Finalizado"].index(doc.get('estado', 'Pendiente')))
                
                materia = st.text_area("Materia", value=doc.get('materia', ''))
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.form_submit_button("💾 Actualizar", use_container_width=True):
                        try:
                            datos_update = (
                                via_doc, remitente, localidad, num_oficio, subclasif,
                                fecha_doc, materia, responsable, referencia, estado
                            )
                            actualizar_documento_recepcion(doc_id, datos_update)
                            st.success("✅ Documento actualizado exitosamente")
                            del st.session_state['doc_editar']
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al actualizar: {str(e)}")
                
                with col_btn2:
                    if st.form_submit_button("🗑️ Eliminar", use_container_width=True):
                        try:
                            eliminar_documento_recepcion(doc_id)
                            st.success("✅ Documento eliminado exitosamente")
                            del st.session_state['doc_editar']
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al eliminar: {str(e)}")
    
    with tab3:
        st.subheader("Lista de Documentos de Recepción")
        
        conn = sqlite3.connect('correspondencia.db')
        df_all = pd.read_sql_query('''
            SELECT id_recepcion as ID, nom_remitente as Remitente,
                   num_oficio as Oficio, fecha_documento as "Fecha Doc",
                   fecha_recepcion as "Fecha Recep", materia as Materia,
                   estado as Estado
            FROM recepcion_documentos
            ORDER BY fecha_recepcion DESC
        ''', conn)
        conn.close()
        
        if not df_all.empty:
            st.dataframe(df_all, use_container_width=True, hide_index=True)
            
            # Exportar a Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_all.to_excel(writer, index=False, sheet_name='Recepción')
            
            st.download_button(
                label="📥 Exportar a Excel",
                data=buffer.getvalue(),
                file_name=f"recepcion_documentos_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No hay documentos registrados")

def gestionar_despacho():
    """Gestiona el despacho de documentos"""
    st.header("📤 Gestión de Despacho de Documentos")
    st.info("Módulo de Despacho - Similar a Recepción pero para documentos salientes")
    
    # Similar estructura a gestionar_recepcion pero para tabla despacho_documentos
    st.markdown("Esta sección permite gestionar documentos que se envían desde la institución.")

def busqueda_avanzada():
    """Búsqueda avanzada de documentos"""
    st.header("🔍 Búsqueda Avanzada")
    
    with st.form("form_busqueda"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            remitente = st.text_input("Remitente")
            oficio = st.text_input("Número Oficio")
        
        with col2:
            fecha_desde = st.date_input("Fecha Desde", value=None)
            fecha_hasta = st.date_input("Fecha Hasta", value=None)
        
        with col3:
            estado = st.selectbox("Estado", ["Todos", "Pendiente", "En Proceso", "Finalizado"])
        
        submitted = st.form_submit_button("🔍 Buscar", use_container_width=True)
        
        if submitted:
            filtros = {
                'remitente': remitente if remitente else None,
                'oficio': oficio if oficio else None,
                'fecha_desde': fecha_desde if fecha_desde else None,
                'fecha_hasta': fecha_hasta if fecha_hasta else None,
                'estado': estado if estado != "Todos" else None
            }
            
            df_resultados = buscar_documentos_recepcion(filtros)
            
            if not df_resultados.empty:
                st.success(f"✅ Se encontraron {len(df_resultados)} documentos")
                st.dataframe(df_resultados, use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ No se encontraron documentos con los criterios especificados")

def mostrar_alertas():
    """Muestra alertas de documentos próximos a vencer"""
    st.header("⚠️ Alertas de Vencimiento")
    
    df_alertas = obtener_alertas_vencimiento()
    
    if not df_alertas.empty:
        hoy = date.today()
        
        for idx, row in df_alertas.iterrows():
            fecha_vcto = datetime.strptime(row['fecha_vcto'], '%Y-%m-%d').date()
            dias_restantes = (fecha_vcto - hoy).days
            
            if dias_restantes < 0:
                tipo_alerta = "error"
                icono = "🔴"
                texto = f"VENCIDO hace {abs(dias_restantes)} días"
            elif dias_restantes == 0:
                tipo_alerta = "warning"
                icono = "🟡"
                texto = "VENCE HOY"
            else:
                tipo_alerta = "info"
                icono = "🟢"
                texto = f"Vence en {dias_restantes} días"
            
            with st.expander(f"{icono} {row['remitente']} - {row['num_oficio']} ({texto})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Remitente:** {row['nom_remitente']}")
                    st.write(f"**Oficio:** {row['num_oficio']}")
                    st.write(f"**Fecha Documento:** {row['fecha_documento']}")
                with col2:
                    st.write(f"**Fecha Vencimiento:** {row['fecha_vcto']}")
                    st.write(f"**Responsable:** {row['nombre_responsable']}")
                    st.write(f"**Referencia:** {row['referencia']}")
                
                st.write(f"**Materia:** {row['materia']}")
    else:
        st.success("✅ No hay documentos próximos a vencer")

def mostrar_estadisticas():
    """Muestra estadísticas del sistema"""
    st.header("📊 Estadísticas")
    
    stats = obtener_estadisticas()
    
    # Gráfico de documentos por remitente
    if not stats['por_remitente'].empty:
        st.subheader("Top 10 Remitentes")
        st.bar_chart(stats['por_remitente'].set_index('nom_remitente')['cantidad'])
    
    # Estadísticas por estado
    conn = sqlite3.connect('correspondencia.db')
    df_estados = pd.read_sql_query('''
        SELECT estado, COUNT(*) as cantidad
        FROM recepcion_documentos
        GROUP BY estado
    ''', conn)
    conn.close()
    
    if not df_estados.empty:
        st.subheader("Documentos por Estado")
        st.bar_chart(df_estados.set_index('estado')['cantidad'])

def configuracion():
    """Configuración del sistema"""
    st.header("⚙️ Configuración")
    
    tab1, tab2 = st.tabs(["👤 Usuario", "🗄️ Base de Datos"])
    
    with tab1:
        st.subheader("Información del Usuario")
        usuario = st.text_input("Nombre de Usuario", value=st.session_state.get('usuario', 'Admin'))
        if st.button("Guardar"):
            st.session_state['usuario'] = usuario
            st.success("Usuario actualizado")
    
    with tab2:
        st.subheader("Gestión de Base de Datos")
        if st.button("🔄 Reiniciar Base de Datos"):
            if st.checkbox("Estoy seguro de eliminar todos los datos"):
                Path('correspondencia.db').unlink(missing_ok=True)
                init_database()
                st.success("Base de datos reiniciada")
                st.rerun()

# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    main()

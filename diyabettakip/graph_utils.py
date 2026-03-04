"""
Graph utilities for Diyabet Takip Sistemi
Provides visualization functions using matplotlib and numpy
"""
import matplotlib.pyplot as plt
import numpy as np
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QVBoxLayout, QWidget
import mysql.connector
from datetime import datetime, time, timedelta  # Added timedelta import
import io
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

# Import config
try:
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
except ImportError:
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "YOUR_PASSWORD"
    DB_NAME = "diyabet"
    DB_CHARSET = "utf8mb4"

# Configure matplotlib for better integration with Qt
matplotlib.use('Qt5Agg')
plt.style.use('ggplot')

# Import constants
from seker_utils import OLCUM_ZAMANLARI, SEKER_SEVIYELERI

def ensure_insulin_saat_column():
    """Make sure the saat column exists in InsulinKayitlari table"""
    import mysql.connector
    
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset=DB_CHARSET
        )
        cursor = conn.cursor()
        
        # Check if saat column exists
        cursor.execute("SHOW COLUMNS FROM InsulinKayitlari LIKE 'saat'")
        column_exists = cursor.fetchone()
        
        if not column_exists:
            print("Adding missing 'saat' column to InsulinKayitlari table...")
            cursor.execute("ALTER TABLE InsulinKayitlari ADD COLUMN saat TIME DEFAULT NULL COMMENT 'İnsülin kullanım saati' AFTER tarih")
            conn.commit()
            print("Added saat column successfully")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error ensuring saat column: {e}")
        return False

# Call the function to ensure the column exists - do this early in the file
ensure_insulin_saat_column()

def convert_to_datetime(date_obj, time_obj):
    """
    Convert any time-like object to a datetime object combined with the given date.
    Handles MySQL timedelta objects, Python time objects, strings, etc.
    
    Args:
        date_obj: A date object to use as the date part
        time_obj: A time-like object (timedelta, time, str, etc.)
        
    Returns:
        datetime object with the correct time
    """
    from datetime import datetime, time, timedelta
    
    # Default time (noon) if we can't convert
    default_time = time(12, 0, 0)
    result_time = default_time
    
    try:
        if time_obj is None:
            return datetime.combine(date_obj, default_time)
            
        # Case 1: Already a time object
        if isinstance(time_obj, time):
            result_time = time_obj
            
        # Case 2: MySQL returns TIME as timedelta
        elif isinstance(time_obj, timedelta):
            # Convert timedelta to time
            total_seconds = time_obj.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            
            # Handle potential overflow (times > 24 hours)
            hours = hours % 24
            result_time = time(hour=hours, minute=minutes, second=seconds)
            
        # Case 3: String in format HH:MM:SS
        elif isinstance(time_obj, str) and ':' in time_obj:
            parts = time_obj.split(':')
            hours = int(parts[0]) % 24
            minutes = int(parts[1]) if len(parts) > 1 else 0
            seconds = int(parts[2]) if len(parts) > 2 else 0
            result_time = time(hour=hours, minute=minutes, second=seconds)
            
        # Case 4: A datetime object (extract its time)
        elif hasattr(time_obj, 'hour') and hasattr(time_obj, 'minute'):
            result_time = time(hour=time_obj.hour, minute=time_obj.minute, 
                             second=getattr(time_obj, 'second', 0))
    except Exception as e:
        print(f"Time conversion error: {e} - using default time")
        result_time = default_time
        
    # Final combination
    return datetime.combine(date_obj, result_time)

def create_blood_sugar_graph(hasta_tc, selected_date):
    """
    Create a blood sugar graph for the selected date
    
    Args:
        hasta_tc: Patient's TC number
        selected_date: Date for which to create the graph
    
    Returns:
        matplotlib Figure object
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime, timedelta, time
    import mysql.connector
    from decimal import Decimal
    
    # Setup connection
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset=DB_CHARSET
    )
    cursor = conn.cursor()
    
    # Get blood sugar measurements for the day
    cursor.execute("""
        SELECT olcum_zamani, saat, seker_seviyesi, seviye_durumu
        FROM KanSekeriKayitlari
        WHERE tc_kimlik_no = %s AND tarih = %s
        ORDER BY saat
    """, (hasta_tc, selected_date))
    
    blood_sugar_results = cursor.fetchall()
    
    # Check if saat column exists in InsulinKayitlari table
    cursor.execute("SHOW COLUMNS FROM InsulinKayitlari LIKE 'saat'")
    saat_exists = cursor.fetchone() is not None
    
    # Get insulin records for the day - now properly using saat field
    cursor.execute("""
        SELECT saat, doz, kullanildi
        FROM InsulinKayitlari
        WHERE hasta_tc = %s AND tarih = %s
    """, (hasta_tc, selected_date))
    
    insulin_results = cursor.fetchall()
    
    # Create figure with primary and secondary y-axes
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # Secondary y-axis for insulin
    ax2 = ax1.twinx()
    
    # Time points for x-axis
    times = []
    sugar_levels = []
    status_colors = []
    
    # Process blood sugar data
    for olcum_zamani, saat, seker_seviyesi, seviye_durumu in blood_sugar_results:
        # Use the helper function to convert time
        time_point = convert_to_datetime(selected_date, saat)
        
        times.append(time_point)
        sugar_levels.append(float(seker_seviyesi))
        
        # Determine color based on status
        if seviye_durumu == 'Dusuk':
            status_colors.append('blue')
        elif seviye_durumu == 'Normal':
            status_colors.append('green')
        elif seviye_durumu == 'Orta':
            status_colors.append('orange')
        elif seviye_durumu == 'Yuksek':
            status_colors.append('red')
        elif seviye_durumu == 'CokYuksek':
            status_colors.append('darkred')
        else:
            status_colors.append('gray')
    
    # Process insulin data - completely rewritten to fix time handling
    insulin_times = []
    insulin_doses = []
    insulin_colors = []
    
    for saat, doz, kullanildi in insulin_results:
        # Use the helper function to convert time
        time_point = convert_to_datetime(selected_date, saat)
        
        insulin_times.append(time_point)
        insulin_doses.append(float(doz))
        
        # Color based on whether insulin was used
        if kullanildi is None:
            insulin_colors.append('gray')  # Status unknown
        elif kullanildi:
            insulin_colors.append('green')  # Used
        else:
            insulin_colors.append('red')    # Not used
    
    # Define a default value for y_max before any conditional blocks
    y_max = 200  # Default maximum value if no data
    
    # Plot blood sugar data with colored points
    if times and sugar_levels:
        # Line plot for blood sugar
        ax1.plot(times, sugar_levels, 'o-', color='#2196F3', linewidth=2, label='Kan Şekeri')
        
        # Scatter plot with colors indicating status
        for i in range(len(times)):
            ax1.scatter(times[i], sugar_levels[i], color=status_colors[i], s=80, zorder=3)
            
        # Update y_max based on actual data if it exists
        y_max = max(sugar_levels, default=200) * 1.1
    
    # Plot insulin data with vertical lines instead of bars
    if insulin_times and insulin_doses:
        # Draw vertical lines for insulin instead of bars
        for i, (time_point, dose, color) in enumerate(zip(insulin_times, insulin_doses, insulin_colors)):
            # Draw vertical line for insulin
            line = ax1.axvline(x=time_point, ymin=0, ymax=0.9, color=color, linewidth=3, 
                       alpha=0.7, linestyle='-', zorder=2, label='İnsülin' if i == 0 else "")
            
            # Add insulin dose text above the line
            ax1.annotate(f'{dose} ml', 
                        xy=(time_point, y_max * 0.95),  # Position at 95% of y-axis
                        xytext=(0, 0),                  # No offset
                        textcoords='offset points',
                        ha='center', 
                        va='bottom',
                        fontweight='bold',
                        fontsize=10,
                        color=color,
                        bbox=dict(boxstyle="round,pad=0.3", fc='white', ec=color, alpha=0.8))
    
    # Set labels and title
    ax1.set_xlabel('Saat')
    ax1.set_ylabel('Kan Şekeri (mg/dL)')
    
    plt.title(f'Kan Şekeri ve İnsülin Grafiği - {selected_date.strftime("%d.%m.%Y")}')
    
    # Add colored reference regions based on blood sugar levels
    # Replace the existing reference lines and area with multiple colored regions
    
    # Low (blue)
    ax1.axhspan(0, 70, alpha=0.1, color='lightblue', label='_nolegend_')
    
    # Normal (green)
    ax1.axhspan(70, 120, alpha=0.1, color='lightgreen', label='_nolegend_')
    
    # Medium/Moderate (yellow)
    ax1.axhspan(120, 180, alpha=0.1, color='yellow', label='_nolegend_')
    
    # High (orange)
    ax1.axhspan(180, 250, alpha=0.1, color='orange', label='_nolegend_')
    
    # Very High (red)
    ax1.axhspan(250, 1000, alpha=0.1, color='lightcoral', label='_nolegend_')
    
    # Add reference lines at important thresholds
    ax1.axhline(y=70, color='blue', linestyle='--', alpha=0.5, label='_nolegend_')
    ax1.axhline(y=120, color='green', linestyle='--', alpha=0.5, label='_nolegend_')
    ax1.axhline(y=180, color='orange', linestyle='--', alpha=0.5, label='_nolegend_')
    ax1.axhline(y=250, color='red', linestyle='--', alpha=0.5, label='_nolegend_')
    
    # Format x-axis as time
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    # Add grid
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    # Set y-axis limits - use y_max which is now always defined
    ax1.set_ylim(0, y_max)
    
    # Add combined legend - remove ax2 related code since we're not using secondary y-axis anymore
    lines, labels = ax1.get_legend_handles_labels()
    ax1.legend(lines, labels, loc='upper left')
    
    # Add value labels for blood sugar
    for i, (time, level) in enumerate(zip(times, sugar_levels)):
        ax1.annotate(f'{level}', 
                    (time, level),
                    xytext=(0, 10), 
                    textcoords='offset points',
                    ha='center', 
                    fontweight='bold',
                    fontsize=9)
    
    # Adjust layout
    fig.tight_layout()
    
    conn.close()
    return fig

def create_weekly_graph(hasta_tc, end_date, start_date=None):
    """
    Create a weekly graph showing blood sugar averages and insulin usage for a date range
    
    Args:
        hasta_tc: Patient's TC number
        end_date: End date for the graph period
        start_date: Optional start date (default is end_date - 7 days)
    
    Returns:
        matplotlib Figure object
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import timedelta
    import mysql.connector
    import numpy as np
    
    # Setup connection
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset=DB_CHARSET
    )
    cursor = conn.cursor()
    
    # Calculate start_date if not provided
    if start_date is None:
        start_date = end_date - timedelta(days=6)  # 7 days including end_date
    
    # Get daily blood sugar averages
    cursor.execute("""
        SELECT tarih, AVG(seker_seviyesi) as avg_sugar
        FROM KanSekeriKayitlari
        WHERE tc_kimlik_no = %s 
        AND tarih BETWEEN %s AND %s
        AND ortalamaya_dahil = TRUE
        GROUP BY tarih
        ORDER BY tarih
    """, (hasta_tc, start_date, end_date))
    
    sugar_results = cursor.fetchall()
    
    # Get daily insulin usage totals
    cursor.execute("""
        SELECT tarih, SUM(doz) as total_insulin
        FROM InsulinKayitlari
        WHERE hasta_tc = %s 
        AND tarih BETWEEN %s AND %s
        GROUP BY tarih
        ORDER BY tarih
    """, (hasta_tc, start_date, end_date))
    
    insulin_results = cursor.fetchall()
    
    # Create figure with primary and secondary y-axes
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Secondary y-axis for insulin
    ax2 = ax1.twinx()
    
    # Process blood sugar data
    days = []
    day_names = []
    sugar_values = []
    
    # Generate date range
    current_date = start_date
    while current_date <= end_date:
        days.append(current_date)
        day_names.append(current_date.strftime("%d.%m"))
        # Default to None (no data)
        sugar_values.append(None)
        current_date += timedelta(days=1)
    
    # Fill in actual blood sugar data
    for row in sugar_results:
        day_index = (row[0] - start_date).days
        if 0 <= day_index < len(sugar_values):
            sugar_values[day_index] = float(row[1])
    
    # Process insulin data
    insulin_values = [0] * len(days)  # Initialize with zeros
    
    for row in insulin_results:
        day_index = (row[0] - start_date).days
        if 0 <= day_index < len(insulin_values):
            insulin_values[day_index] = float(row[1]) if row[1] is not None else 0
    
    # Convert None to NaN for plotting
    plot_sugar = [float(v) if v is not None else np.nan for v in sugar_values]
    
    # Plot blood sugar data (line)
    ax1.plot(days, plot_sugar, 'o-', color='#2196F3', linewidth=2, markersize=8, label='Kan Şekeri Ortalaması')
    
    # Define y_max for insulin annotations
    all_values = [v for v in plot_sugar if not np.isnan(v)]
    y_max = max(all_values, default=200) * 1.1
    
    # Plot insulin data with vertical lines instead of bars
    if max(insulin_values) > 0:
        # Draw vertical lines for insulin instead of bars
        for i, (day, dose) in enumerate(zip(days, insulin_values)):
            if dose > 0:  # Only draw for days with insulin
                # Draw vertical line for insulin
                line = ax1.axvline(x=day, ymin=0, ymax=0.9, color='#4CAF50', linewidth=3, 
                        alpha=0.7, linestyle='-', zorder=2, label='İnsülin' if i == 0 and dose > 0 else "")
                
                # Add insulin dose text above the line
                ax1.annotate(f'{dose:.1f} ml', 
                            xy=(day, y_max * 0.95),  # Position at 95% of y-axis
                            xytext=(0, 0),           # No offset
                            textcoords='offset points',
                            ha='center', 
                            va='bottom',
                            fontweight='bold',
                            fontsize=10,
                            color='#4CAF50',
                            bbox=dict(boxstyle="round,pad=0.3", fc='white', ec='#4CAF50', alpha=0.8))
    
    # Set labels and title
    ax1.set_xlabel('Tarih')
    ax1.set_ylabel('Ortalama Kan Şekeri (mg/dL)')
    ax2.set_ylabel('Toplam Günlük İnsülin (ml)')
    
    plt.title(f'Haftalık Kan Şekeri ve İnsülin Grafiği\n{start_date.strftime("%d.%m.%Y")} - {end_date.strftime("%d.%m.%Y")}')
    
    # Add reference lines for blood sugar
    ax1.axhline(y=70, color='blue', linestyle='--', alpha=0.5)  # Lower limit
    ax1.axhline(y=180, color='red', linestyle='--', alpha=0.5)  # Upper limit
    
    # Add reference area
    ax1.axhspan(70, 180, alpha=0.1, color='green')
    
    # Format x-axis
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
    
    # Add grid
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    # Add value labels for blood sugar
    for i, value in enumerate(sugar_values):
        if value is not None:
            ax1.annotate(f'{float(value):.1f}', 
                        (days[i], float(value)),
                        xytext=(0, 10), 
                        textcoords='offset points',
                        ha='center', 
                        fontweight='bold')
    
    # Add combined legend - use only ax1 now
    lines, labels = ax1.get_legend_handles_labels()
    ax1.legend(lines, labels, loc='upper left')
    
    # Set y-axis limits with some padding
    all_values = [v for v in plot_sugar if not np.isnan(v)]
    if all_values:
        min_val = min(min(all_values), 70) - 10
        max_val = max(max(all_values), 180) + 10
        ax1.set_ylim(min_val, max_val)
    else:
        ax1.set_ylim(0, 200)
    
    # We don't need separate y-axis limits for insulin since we're using vertical lines
    # instead of a secondary y-axis
    
    # Adjust layout
    plt.tight_layout()
    
    conn.close()
    return fig
def embed_matplotlib_figure(layout, figure):
    """Embed a matplotlib figure in a PyQt layout"""
    # Clear any existing widgets in layout
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()
    
    # Create a canvas and add the figure to it
    canvas = FigureCanvas(figure)
    
    # Set size policy to make the canvas expand in both directions
    from PyQt5.QtWidgets import QSizePolicy
    canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    
    # Force the canvas to take up as much space as possible
    canvas.setMinimumHeight(400)  # Set a reasonable minimum height
    
    layout.addWidget(canvas)
    
    return canvas

def pixmap_from_figure(figure):
    """Convert a matplotlib figure to a QPixmap"""
    # Save figure to in-memory buffer
    buf = io.BytesIO()
    figure.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    
    # Create QImage from buffer
    image = QImage.fromData(buf.getvalue())
    
    # Convert QImage to QPixmap
    pixmap = QPixmap.fromImage(image)
    
    return pixmap

# Helper function to safely format any time/date object
def safe_format_time(time_obj, format_str='%H:%M'):
    """
    Safely format a time object, handling different types
    
    Args:
        time_obj: The time object to format (time, datetime, timedelta, or string)
        format_str: The format string to use (default: '%H:%M')
        
    Returns:
        str: The formatted time string
    """
    from datetime import time, datetime, timedelta
    
    try:
        if isinstance(time_obj, (time, datetime)):
            return time_obj.strftime(format_str)
        elif isinstance(time_obj, timedelta):
            # Convert timedelta to hours:minutes format
            total_seconds = int(time_obj.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}"
        elif isinstance(time_obj, str):
            # If it's already a string, just return it
            return time_obj
        else:
            return '—'
    except Exception as e:
        print(f"Error formatting time: {e}")
        return '—'

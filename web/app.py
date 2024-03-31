from pathlib import Path
current_directory = Path(__file__).parent.parent
current_directory_str = str(current_directory).replace('\\', '/')
import sys
sys.path.append(current_directory_str)


from flask import Flask, render_template
app = Flask(__name__)

from web.db_interactions import get_open_positions, get_closed_positions

@app.route('/')
def index():
    open_positions = get_open_positions()
    closed_positions = get_closed_positions()
    return render_template(
        'index.html', 
        open_positions=open_positions, 
        closed_positions=closed_positions
    )


if __name__ == '__main__':
    app.run(debug=True)
#!/usr/bin/env bash

set -e 

APPNAME="applol"


echo "🐍 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created."
else
    echo "✅ Virtual environment already exists."
fi

# 3. Install Python Dependencies
echo "⬇️  Installing Python libraries (textual, requests, bs4, yt-dlp)..."
source venv/bin/activate
pip install ../requirements.txt
echo "✅ Dependencies installed."

# 4. Create the launcher wrapper
echo "🚀 Creating launcher script..."
cat << 'EOF' > "$APPNAME"
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"
export PATH="$SCRIPT_DIR/venv/bin:$PATH"
streamlit run "$SCRIPT_DIR/pylol.py" "$@"
EOF

chmod +x "$APPNAME"
echo ""
echo "🎉 Setup complete!"
echo "Run the $APPNAME with:"
echo "  ./$APPNAME"

# .bashrc
# Source global definitions
if [ -f /etc/bashrc ]; then
    . /etc/bashrc
fi

# Load environment variables
if [ -f "$HOME/.env" ]; then
    set -a
    source "$HOME/.env"
    set +a
fi

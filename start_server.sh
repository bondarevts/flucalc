#!/bin/bash

# Default values
ip="127.0.0.1"
port="5000"
workers_count=4

# Parse arguments
for arg in "$@"; do
    if [[ "$arg" == *:* ]]; then
        ip="${arg%%:*}"
        port="${arg##*:}"
        break
    elif [[ "$arg" == *.* ]]; then
        ip="$arg"
    elif [[ "$arg" =~ ^[0-9]+$ ]]; then
        port="$arg"
    fi
done

echo "FluCalc started on http://$ip:$port"

# Run gunicorn with the given values
gunicorn -w "$workers_count" -b "$ip:$port" flucalc:app

#!/bin/bash
# utils.sh - Common utilities for scripts
# This file contains common functions and color definitions used across scripts

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Printing functions
print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_header() { echo -e "\n${BOLD}${GREEN}==== $1 ====${NC}\n"; }
print_title() { echo -e "${CYAN}•${NC} $1\n"; }
print_step() { echo -e "${CYAN}[STEP]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_code() { echo -e "  ${CYAN}$1${NC}"; } 
# Milk Inventory Frontend

A modular React.js frontend application for the Milk Inventory system.

## Setup

1. Navigate to the frontend directory:
   ```bash
   cd c:\Users\Thinkpad\sourcecode\MilkInventory-Frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open in browser:
   ```text
   http://localhost:3000
   ```

## Build for Production

```bash
npm run build
```

Output will be in the `dist` folder.

## Features

- **Units Management** - CRUD operations for units
- **SKUs Management** - CRUD operations for SKUs
- **Tab Navigation** - Switch between Units and SKUs
- **API Proxy** - Frontend proxies requests to backend (`http://localhost:8000`)

## Architecture

- **Vite** - Build tool and dev server
- **React 18** - UI framework
- **Axios** - HTTP client
- **Modern CSS** - Responsive styling

## Environment Notes

Ensure the backend is running on `http://localhost:8000` before starting the frontend.

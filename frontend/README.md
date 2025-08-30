# DeepSearch Frontend

A modern, responsive web interface for the DeepSearch AI system built with Next.js 14, TypeScript, and Tailwind CSS.

## Features

- 🔍 **Google-like Search Interface**: Clean, intuitive search experience
- 🧠 **Real-time Thinking Process**: Collapsible dropdown showing AI's step-by-step reasoning
- ⚡ **WebSocket Integration**: Live updates for search progress
- 📱 **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- 🎨 **Modern UI**: Built with shadcn/ui components and Tailwind CSS
- 🔄 **New Chat Functionality**: Reset sessions with a single click

## Quick Start

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Set environment variables**:
   ```bash
   # Optional - defaults to localhost
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_WS_URL=ws://localhost:8000
   ```

3. **Run the development server**:
   ```bash
   npm run dev
   ```

4. **Open your browser**:
   Navigate to [http://localhost:3000](http://localhost:3000)

## Architecture

### Components Structure
- **SearchBox**: Main search input with new chat functionality
- **ThinkingProcess**: Collapsible container showing reasoning steps
- **StepCard**: Individual step display with expandable details
- **FinalAnswer**: Results presentation with copy/share features
- **SearchResults**: Orchestrates all search-related components

### State Management
- **Zustand Store**: Lightweight state management for search data
- **WebSocket Hook**: Real-time communication with backend
- **Type Safety**: Full TypeScript coverage with defined interfaces

### UI Components
- **shadcn/ui**: Modern, accessible component library
- **Tailwind CSS**: Utility-first styling with custom animations
- **Responsive Design**: Mobile-first approach with smooth transitions

## Usage

1. **Start a Search**: Type your question and press Enter or click Search
2. **Watch the Process**: Expand the "Thinking..." section to see AI reasoning
3. **View Results**: Get detailed answers with sources and metadata
4. **New Chat**: Click the "+" button to reset and start fresh
5. **Copy/Share**: Use built-in tools to save or share results

## Development

### Scripts
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

### Key Files
- `src/app/page.tsx` - Main page component
- `src/hooks/useSearch.tsx` - Search state management
- `src/hooks/useWebSocket.tsx` - WebSocket connection
- `src/lib/api.ts` - Backend API client
- `src/types/` - TypeScript type definitions

## Configuration

The frontend automatically connects to the backend API. Default configuration:
- **API URL**: `http://localhost:8000`
- **WebSocket URL**: `ws://localhost:8000`
- **Auto-reconnect**: Enabled with exponential backoff

## Browser Support

- Chrome/Edge 88+
- Firefox 85+
- Safari 14+
- Mobile browsers with WebSocket support

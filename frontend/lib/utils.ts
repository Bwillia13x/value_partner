import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(
  amount: number,
  options: {
    currency?: string
    minimumFractionDigits?: number
    maximumFractionDigits?: number
  } = {}
) {
  const {
    currency = "USD",
    minimumFractionDigits = 0,
    maximumFractionDigits = 2
  } = options

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(amount)
}

export function formatPercentage(
  value: number,
  options: {
    minimumFractionDigits?: number
    maximumFractionDigits?: number
  } = {}
) {
  const {
    minimumFractionDigits = 0,
    maximumFractionDigits = 2
  } = options

  return new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(value / 100)
}

export function formatNumber(
  value: number,
  options: {
    minimumFractionDigits?: number
    maximumFractionDigits?: number
    notation?: "standard" | "scientific" | "engineering" | "compact"
  } = {}
) {
  const {
    minimumFractionDigits = 0,
    maximumFractionDigits = 2,
    notation = "standard"
  } = options

  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits,
    maximumFractionDigits,
    notation,
  }).format(value)
}

export function formatDate(
  date: Date | string,
  options: {
    dateStyle?: "full" | "long" | "medium" | "short"
    timeStyle?: "full" | "long" | "medium" | "short"
  } = {}
) {
  const {
    dateStyle = "medium",
    timeStyle
  } = options

  const dateObj = typeof date === "string" ? new Date(date) : date

  return new Intl.DateTimeFormat("en-US", {
    dateStyle,
    timeStyle,
  }).format(dateObj)
}

export function getPercentageColor(value: number) {
  if (value > 0) return "text-green-600"
  if (value < 0) return "text-red-600"
  return "text-gray-600"
}

export function getPercentageBackgroundColor(value: number) {
  if (value > 0) return "bg-green-50"
  if (value < 0) return "bg-red-50"
  return "bg-gray-50"
}

export function calculatePercentageChange(oldValue: number, newValue: number) {
  if (oldValue === 0) return 0
  return ((newValue - oldValue) / oldValue) * 100
}

export function debounce<T extends (...args: any[]) => void>(
  func: T,
  wait: number
): T {
  let timeout: NodeJS.Timeout | null = null
  return ((...args: any[]) => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }) as T
}

export function throttle<T extends (...args: any[]) => void>(
  func: T,
  limit: number
): T {
  let inThrottle: boolean
  return ((...args: any[]) => {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }) as T
}

export function isValidEmail(email: string) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

export function generateRandomColor() {
  const colors = [
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
    "#06B6D4", "#84CC16", "#F97316", "#EC4899", "#6366F1"
  ]
  return colors[Math.floor(Math.random() * colors.length)]
}

export function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export function getInitials(name: string) {
  return name
    .split(" ")
    .map(word => word.charAt(0))
    .join("")
    .toUpperCase()
    .slice(0, 2)
}

export function truncateText(text: string, maxLength: number) {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + "..."
}

export function capitalizeFirstLetter(string: string) {
  return string.charAt(0).toUpperCase() + string.slice(1)
}

export function kebabCase(str: string) {
  return str
    .replace(/([a-z])([A-Z])/g, "$1-$2")
    .replace(/[\s_]+/g, "-")
    .toLowerCase()
}

export function camelCase(str: string) {
  return str
    .replace(/[-_\s]+(.)?/g, (_, c) => (c ? c.toUpperCase() : ""))
    .replace(/^[A-Z]/, (c) => c.toLowerCase())
}

export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== "object") return obj
  if (obj instanceof Date) return new Date(obj.getTime()) as T
  if (obj instanceof Array) return obj.map(item => deepClone(item)) as T
  if (typeof obj === "object") {
    const clonedObj = {} as T
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        clonedObj[key] = deepClone(obj[key])
      }
    }
    return clonedObj
  }
  return obj
}

export function objectToQueryString(obj: Record<string, any>) {
  return Object.entries(obj)
    .filter(([_, value]) => value !== null && value !== undefined)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join("&")
}

export function queryStringToObject(queryString: string) {
  const params = new URLSearchParams(queryString)
  const obj: Record<string, string> = {}
  for (const [key, value] of params.entries()) {
    obj[key] = value
  }
  return obj
}

export function downloadFile(data: Blob, filename: string) {
  const url = URL.createObjectURL(data)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function copyToClipboard(text: string) {
  return navigator.clipboard.writeText(text)
}

export function getRandomId() {
  return Math.random().toString(36).substr(2, 9)
}

export function isClient() {
  return typeof window !== "undefined"
}

export function isMobile() {
  if (!isClient()) return false
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
}

export function getDeviceType() {
  if (!isClient()) return "desktop"
  if (isMobile()) return "mobile"
  return "desktop"
}

export function getViewportSize() {
  if (!isClient()) return { width: 0, height: 0 }
  return {
    width: window.innerWidth,
    height: window.innerHeight
  }
}

export function scrollToElement(elementId: string, offset: number = 0) {
  const element = document.getElementById(elementId)
  if (element) {
    const elementPosition = element.offsetTop
    const offsetPosition = elementPosition - offset
    window.scrollTo({
      top: offsetPosition,
      behavior: "smooth"
    })
  }
}

export function smoothScrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: "smooth"
  })
}

export function isElementInViewport(element: HTMLElement) {
  const rect = element.getBoundingClientRect()
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  )
}

export function parseJwt(token: string) {
  try {
    return JSON.parse(atob(token.split('.')[1]))
  } catch (e) {
    return null
  }
}

export function isTokenExpired(token: string) {
  const decoded = parseJwt(token)
  if (!decoded) return true
  const currentTime = Date.now() / 1000
  return decoded.exp < currentTime
}

export function formatFileSize(bytes: number) {
  if (bytes === 0) return "0 Bytes"
  const k = 1024
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
}

export function validatePassword(password: string) {
  const minLength = 8
  const hasUpperCase = /[A-Z]/.test(password)
  const hasLowerCase = /[a-z]/.test(password)
  const hasNumbers = /\d/.test(password)
  const hasNonalphas = /\W/.test(password)
  
  return {
    isValid: password.length >= minLength && hasUpperCase && hasLowerCase && hasNumbers && hasNonalphas,
    minLength: password.length >= minLength,
    hasUpperCase,
    hasLowerCase,
    hasNumbers,
    hasSpecialChar: hasNonalphas
  }
}

export function generatePassword(length: number = 12) {
  const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?"
  let password = ""
  for (let i = 0; i < length; i++) {
    password += charset.charAt(Math.floor(Math.random() * charset.length))
  }
  return password
}

export function colorStringToHex(color: string) {
  const colorMap: Record<string, string> = {
    red: "#EF4444",
    green: "#10B981",
    blue: "#3B82F6",
    yellow: "#F59E0B",
    purple: "#8B5CF6",
    pink: "#EC4899",
    indigo: "#6366F1",
    gray: "#6B7280",
    orange: "#F97316",
    teal: "#14B8A6",
    cyan: "#06B6D4",
    lime: "#84CC16",
  }
  return colorMap[color.toLowerCase()] || color
}

export function hexToRgb(hex: string) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : null
}

export function rgbToHex(r: number, g: number, b: number) {
  return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)
}

export function getContrastColor(hexColor: string) {
  const rgb = hexToRgb(hexColor)
  if (!rgb) return "#000000"
  
  const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000
  return brightness > 128 ? "#000000" : "#FFFFFF"
}

export function lightenColor(hex: string, amount: number) {
  const rgb = hexToRgb(hex)
  if (!rgb) return hex
  
  const r = Math.min(255, Math.max(0, rgb.r + amount))
  const g = Math.min(255, Math.max(0, rgb.g + amount))
  const b = Math.min(255, Math.max(0, rgb.b + amount))
  
  return rgbToHex(r, g, b)
}

export function darkenColor(hex: string, amount: number) {
  return lightenColor(hex, -amount)
}

export function interpolateColor(color1: string, color2: string, factor: number) {
  const rgb1 = hexToRgb(color1)
  const rgb2 = hexToRgb(color2)
  
  if (!rgb1 || !rgb2) return color1
  
  const r = Math.round(rgb1.r + (rgb2.r - rgb1.r) * factor)
  const g = Math.round(rgb1.g + (rgb2.g - rgb1.g) * factor)
  const b = Math.round(rgb1.b + (rgb2.b - rgb1.b) * factor)
  
  return rgbToHex(r, g, b)
}

export function getRandomGradient() {
  const colors = [
    "from-blue-500 to-purple-600",
    "from-green-400 to-blue-500",
    "from-purple-500 to-pink-500",
    "from-yellow-400 to-orange-500",
    "from-red-500 to-yellow-500",
    "from-pink-500 to-rose-500",
    "from-indigo-500 to-purple-500",
    "from-cyan-500 to-blue-500",
    "from-teal-500 to-green-500",
    "from-orange-500 to-red-500",
  ]
  return colors[Math.floor(Math.random() * colors.length)]
}

export function createSafeAsyncFunction<T extends (...args: any[]) => Promise<any>>(
  asyncFn: T,
  fallbackValue?: any
) {
  return async (...args: Parameters<T>): Promise<ReturnType<T> | typeof fallbackValue> => {
    try {
      return await asyncFn(...args)
    } catch (error) {
      console.error("Async function error:", error)
      return fallbackValue
    }
  }
}

export function retryAsync<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  delay: number = 1000
): Promise<T> {
  return new Promise((resolve, reject) => {
    let retries = 0
    
    const attempt = async () => {
      try {
        const result = await fn()
        resolve(result)
      } catch (error) {
        if (retries < maxRetries) {
          retries++
          setTimeout(attempt, delay * Math.pow(2, retries - 1)) // Exponential backoff
        } else {
          reject(error)
        }
      }
    }
    
    attempt()
  })
}

export function memoize<T extends (...args: any[]) => any>(fn: T, getKey?: (...args: Parameters<T>) => string): T {
  const cache = new Map<string, ReturnType<T>>()
  
  return ((...args: Parameters<T>): ReturnType<T> => {
    const key = getKey ? getKey(...args) : JSON.stringify(args)
    
    if (cache.has(key)) {
      return cache.get(key)!
    }
    
    const result = fn(...args)
    cache.set(key, result)
    return result
  }) as T
}

export function createEventEmitter<T extends Record<string, any>>() {
  const listeners: { [K in keyof T]?: Array<(data: T[K]) => void> } = {}
  
  return {
    on<K extends keyof T>(event: K, callback: (data: T[K]) => void) {
      if (!listeners[event]) {
        listeners[event] = []
      }
      listeners[event]!.push(callback)
    },
    
    off<K extends keyof T>(event: K, callback: (data: T[K]) => void) {
      if (listeners[event]) {
        listeners[event] = listeners[event]!.filter(cb => cb !== callback)
      }
    },
    
    emit<K extends keyof T>(event: K, data: T[K]) {
      if (listeners[event]) {
        listeners[event]!.forEach(callback => callback(data))
      }
    },
    
    removeAllListeners<K extends keyof T>(event?: K) {
      if (event) {
        delete listeners[event]
      } else {
        Object.keys(listeners).forEach(key => delete listeners[key as keyof T])
      }
    }
  }
}

export function createQueue<T>() {
  const queue: T[] = []
  let isProcessing = false
  
  return {
    add(item: T) {
      queue.push(item)
    },
    
    async process(processFn: (item: T) => Promise<void>) {
      if (isProcessing) return
      
      isProcessing = true
      
      while (queue.length > 0) {
        const item = queue.shift()!
        await processFn(item)
      }
      
      isProcessing = false
    },
    
    clear() {
      queue.length = 0
    },
    
    get size() {
      return queue.length
    },
    
    get isEmpty() {
      return queue.length === 0
    }
  }
}

export function createLocalStorageManager<T>(key: string, defaultValue: T) {
  return {
    get(): T {
      if (!isClient()) return defaultValue
      try {
        const item = localStorage.getItem(key)
        return item ? JSON.parse(item) : defaultValue
      } catch (error) {
        console.error(`Error reading from localStorage key "${key}":`, error)
        return defaultValue
      }
    },
    
    set(value: T): void {
      if (!isClient()) return
      try {
        localStorage.setItem(key, JSON.stringify(value))
      } catch (error) {
        console.error(`Error writing to localStorage key "${key}":`, error)
      }
    },
    
    remove(): void {
      if (!isClient()) return
      try {
        localStorage.removeItem(key)
      } catch (error) {
        console.error(`Error removing localStorage key "${key}":`, error)
      }
    }
  }
}

export function createSessionStorageManager<T>(key: string, defaultValue: T) {
  return {
    get(): T {
      if (!isClient()) return defaultValue
      try {
        const item = sessionStorage.getItem(key)
        return item ? JSON.parse(item) : defaultValue
      } catch (error) {
        console.error(`Error reading from sessionStorage key "${key}":`, error)
        return defaultValue
      }
    },
    
    set(value: T): void {
      if (!isClient()) return
      try {
        sessionStorage.setItem(key, JSON.stringify(value))
      } catch (error) {
        console.error(`Error writing to sessionStorage key "${key}":`, error)
      }
    },
    
    remove(): void {
      if (!isClient()) return
      try {
        sessionStorage.removeItem(key)
      } catch (error) {
        console.error(`Error removing sessionStorage key "${key}":`, error)
      }
    }
  }
}

export default {
  cn,
  formatCurrency,
  formatPercentage,
  formatNumber,
  formatDate,
  getPercentageColor,
  getPercentageBackgroundColor,
  calculatePercentageChange,
  debounce,
  throttle,
  isValidEmail,
  generateRandomColor,
  sleep,
  getInitials,
  truncateText,
  capitalizeFirstLetter,
  kebabCase,
  camelCase,
  deepClone,
  objectToQueryString,
  queryStringToObject,
  downloadFile,
  copyToClipboard,
  getRandomId,
  isClient,
  isMobile,
  getDeviceType,
  getViewportSize,
  scrollToElement,
  smoothScrollToTop,
  isElementInViewport,
  parseJwt,
  isTokenExpired,
  formatFileSize,
  validatePassword,
  generatePassword,
  colorStringToHex,
  hexToRgb,
  rgbToHex,
  getContrastColor,
  lightenColor,
  darkenColor,
  interpolateColor,
  getRandomGradient,
  createSafeAsyncFunction,
  retryAsync,
  memoize,
  createEventEmitter,
  createQueue,
  createLocalStorageManager,
  createSessionStorageManager
} 
"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bell,
  Search,
  Settings,
  User,
  Menu,
  X,
  Home,
  BarChart3,
  PieChart,
  TrendingUp,
  Zap,
  Bot,
  ChevronDown,
  LogOut,
  CreditCard,
  Wallet,
  DollarSign,
  Building,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";

const NAV_ITEMS = [
  { 
    href: "/", 
    label: "Dashboard", 
    icon: Home,
    description: "Portfolio overview"
  },
  { 
    href: "/portfolio", 
    label: "Portfolio", 
    icon: PieChart,
    description: "Holdings & performance"
  },
  { 
    href: "/trading", 
    label: "Trading", 
    icon: DollarSign,
    description: "Execute trades"
  },
  { 
    href: "/analytics", 
    label: "Analytics", 
    icon: BarChart3,
    description: "Advanced metrics"
  },
  { 
    href: "/factors", 
    label: "Factors", 
    icon: TrendingUp,
    description: "Factor analysis"
  },
  { 
    href: "/backtest", 
    label: "Backtest", 
    icon: Zap,
    description: "Strategy testing"
  },
  { 
    href: "/copilot", 
    label: "AI Copilot", 
    icon: Bot,
    description: "AI assistant"
  },
];

const USER_MENU_ITEMS = [
  { 
    href: "/profile", 
    label: "Profile", 
    icon: User 
  },
  { 
    href: "/billing", 
    label: "Billing", 
    icon: CreditCard 
  },
  { 
    href: "/accounts", 
    label: "Accounts", 
    icon: Building 
  },
  { 
    href: "/settings", 
    label: "Settings", 
    icon: Settings 
  },
];

interface NotificationProps {
  id: string;
  title: string;
  message: string;
  type: "info" | "warning" | "success" | "error";
  timestamp: string;
  read: boolean;
}

export default function NavBar() {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [notifications, setNotifications] = useState<NotificationProps[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  // Mock user data - in real app, get from auth context
  const user = {
    name: "John Doe",
    email: "john.doe@example.com",
    avatar: null,
    initials: "JD",
    accountValue: 1234567.89,
    isDarkMode: false
  };

  useEffect(() => {
    // Close mobile menu when route changes
    setIsMobileMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    // Mock notifications - in real app, fetch from API
    const mockNotifications: NotificationProps[] = [
      {
        id: "1",
        title: "Market Alert",
        message: "AAPL is up 5% today",
        type: "success",
        timestamp: "2 min ago",
        read: false
      },
      {
        id: "2",
        title: "Portfolio Rebalance",
        message: "Your portfolio needs rebalancing",
        type: "warning",
        timestamp: "1 hour ago",
        read: false
      },
      {
        id: "3",
        title: "Dividend Payment",
        message: "Received $125.50 dividend from MSFT",
        type: "info",
        timestamp: "1 day ago",
        read: true
      }
    ];
    setNotifications(mockNotifications);
    setUnreadCount(mockNotifications.filter(n => !n.read).length);
  }, []);

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const toggleUserMenu = () => {
    setIsUserMenuOpen(!isUserMenuOpen);
  };

  const toggleNotifications = () => {
    setIsNotificationsOpen(!isNotificationsOpen);
  };

  const markNotificationAsRead = (id: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    );
    setUnreadCount(prev => Math.max(0, prev - 1));
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case "success": return "🟢";
      case "warning": return "🟡";
      case "error": return "🔴";
      default: return "🔵";
    }
  };

  return (
    <>
      <nav className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60 dark:border-gray-700 dark:bg-gray-900/95">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo */}
            <div className="flex items-center">
              <Link href="/" className="flex items-center space-x-2">
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-purple-600"
                >
                  <DollarSign className="h-5 w-5 text-white" />
                </motion.div>
                <span className="hidden font-bold text-gray-900 dark:text-white sm:block">
                  Value Partner
                </span>
              </Link>
            </div>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center space-x-1">
              {NAV_ITEMS.map(({ href, label, icon: Icon, description }) => {
                const active = pathname === href;
                return (
                  <motion.div key={href} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                    <Link
                      href={href}
                      className={cn(
                        "group relative flex items-center space-x-2 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200",
                        active
                          ? "bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300"
                          : "text-gray-700 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white"
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      <span>{label}</span>
                      {active && (
                        <motion.div
                          layoutId="activeTab"
                          className="absolute inset-0 rounded-lg bg-blue-50 dark:bg-blue-900/50"
                          style={{ zIndex: -1 }}
                          transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                        />
                      )}
                      
                      {/* Tooltip */}
                      <div className="absolute top-full left-1/2 transform -translate-x-1/2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
                        <div className="bg-gray-900 text-white text-xs rounded-md px-2 py-1 whitespace-nowrap">
                          {description}
                          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-b-gray-900"></div>
                        </div>
                      </div>
                    </Link>
                  </motion.div>
                );
              })}
            </div>

            {/* Right Side Actions */}
            <div className="flex items-center space-x-2">
              {/* Search */}
              <div className="relative hidden sm:block">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setIsSearchOpen(true)}
                  className="flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 bg-white hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700"
                >
                  <Search className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                </motion.button>
              </div>

              {/* Notifications */}
              <div className="relative">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={toggleNotifications}
                  className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 bg-white hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700"
                >
                  <Bell className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                  {unreadCount > 0 && (
                    <motion.span
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white"
                    >
                      {unreadCount > 9 ? "9+" : unreadCount}
                    </motion.span>
                  )}
                </motion.button>

                {/* Notifications Dropdown */}
                <AnimatePresence>
                  {isNotificationsOpen && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95, y: -10 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95, y: -10 }}
                      className="absolute right-0 top-12 w-80 origin-top-right"
                    >
                      <Card className="shadow-lg border">
                        <CardContent className="p-0">
                          <div className="border-b border-gray-200 p-4">
                            <h3 className="font-semibold">Notifications</h3>
                          </div>
                          <div className="max-h-80 overflow-y-auto">
                            {notifications.length === 0 ? (
                              <div className="p-4 text-center text-gray-500">
                                No notifications
                              </div>
                            ) : (
                              notifications.map((notification) => (
                                <motion.div
                                  key={notification.id}
                                  initial={{ opacity: 0, x: -10 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  onClick={() => markNotificationAsRead(notification.id)}
                                  className={cn(
                                    "border-b border-gray-100 p-4 hover:bg-gray-50 cursor-pointer transition-colors",
                                    !notification.read && "bg-blue-50"
                                  )}
                                >
                                  <div className="flex items-start space-x-3">
                                    <span className="text-lg">
                                      {getNotificationIcon(notification.type)}
                                    </span>
                                    <div className="flex-1 min-w-0">
                                      <p className="text-sm font-medium text-gray-900">
                                        {notification.title}
                                      </p>
                                      <p className="text-sm text-gray-500 truncate">
                                        {notification.message}
                                      </p>
                                      <p className="text-xs text-gray-400 mt-1">
                                        {notification.timestamp}
                                      </p>
                                    </div>
                                    {!notification.read && (
                                      <div className="h-2 w-2 rounded-full bg-blue-500"></div>
                                    )}
                                  </div>
                                </motion.div>
                              ))
                            )}
                          </div>
                          <div className="border-t border-gray-200 p-3">
                            <Button variant="ghost" size="sm" className="w-full">
                              View all notifications
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Account Value (Desktop) */}
              <div className="hidden lg:flex items-center space-x-2 px-3 py-1 bg-green-50 rounded-lg">
                <Wallet className="h-4 w-4 text-green-600" />
                <span className="text-sm font-medium text-green-800">
                  ${user.accountValue.toLocaleString()}
                </span>
              </div>

              {/* User Menu */}
              <div className="relative">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={toggleUserMenu}
                  className="flex items-center space-x-2 rounded-lg border border-gray-200 bg-white p-1.5 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700"
                >
                  {user.avatar ? (
                    <img
                      src={user.avatar}
                      alt={user.name}
                      className="h-7 w-7 rounded-full"
                    />
                  ) : (
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
                      {user.initials}
                    </div>
                  )}
                  <span className="hidden text-sm font-medium text-gray-700 dark:text-gray-300 sm:block">
                    {user.name.split(" ")[0]}
                  </span>
                  <ChevronDown className="h-3 w-3 text-gray-400" />
                </motion.button>

                {/* User Dropdown */}
                <AnimatePresence>
                  {isUserMenuOpen && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95, y: -10 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95, y: -10 }}
                      className="absolute right-0 top-12 w-56 origin-top-right"
                    >
                      <Card className="shadow-lg border">
                        <CardContent className="p-0">
                          <div className="border-b border-gray-200 p-4">
                            <p className="text-sm font-medium text-gray-900">{user.name}</p>
                            <p className="text-sm text-gray-500">{user.email}</p>
                          </div>
                          <div className="py-1">
                            {USER_MENU_ITEMS.map(({ href, label, icon: Icon }) => (
                              <Link
                                key={href}
                                href={href}
                                onClick={() => setIsUserMenuOpen(false)}
                                className="flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800"
                              >
                                <Icon className="h-4 w-4" />
                                <span>{label}</span>
                              </Link>
                            ))}
                          </div>
                          <div className="border-t border-gray-200 py-1">
                            <button className="flex w-full items-center space-x-2 px-4 py-2 text-sm text-red-700 hover:bg-red-50">
                              <LogOut className="h-4 w-4" />
                              <span>Sign out</span>
                            </button>
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Mobile Menu Button */}
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggleMobileMenu}
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 bg-white hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700 md:hidden"
              >
                {isMobileMenuOpen ? (
                  <X className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                ) : (
                  <Menu className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                )}
              </motion.button>
            </div>
          </div>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {isMobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="border-t border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900 md:hidden"
            >
              <div className="space-y-1 px-4 pb-3 pt-2">
                {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
                  const active = pathname === href;
                  return (
                    <Link
                      key={href}
                      href={href}
                      onClick={() => setIsMobileMenuOpen(false)}
                      className={cn(
                        "flex items-center space-x-3 rounded-lg px-3 py-2 text-base font-medium transition-colors",
                        active
                          ? "bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300"
                          : "text-gray-700 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white"
                      )}
                    >
                      <Icon className="h-5 w-5" />
                      <span>{label}</span>
                    </Link>
                  );
                })}
                
                {/* Account Value (Mobile) */}
                <div className="flex items-center justify-between px-3 py-2 mt-4 bg-green-50 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <Wallet className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-medium text-green-800">Account Value</span>
                  </div>
                  <span className="text-sm font-bold text-green-800">
                    ${user.accountValue.toLocaleString()}
                  </span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>

      {/* Search Modal */}
      <AnimatePresence>
        {isSearchOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4"
            onClick={() => setIsSearchOpen(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -20 }}
              className="w-full max-w-lg"
              onClick={(e) => e.stopPropagation()}
            >
              <Card className="shadow-2xl">
                <CardContent className="p-4">
                  <div className="flex items-center space-x-3">
                    <Search className="h-5 w-5 text-gray-400" />
                    <input
                      type="text"
                      placeholder="Search securities, portfolios, or features..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="flex-1 border-none bg-transparent text-lg placeholder-gray-400 focus:outline-none"
                      autoFocus
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setIsSearchOpen(false)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                  
                  {searchQuery && (
                    <div className="mt-4 space-y-2">
                      <p className="text-sm text-gray-500">Search results for &quot;{searchQuery}&quot;</p>
                      <div className="space-y-1">
                        <div className="p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
                          <p className="font-medium">Apple Inc. (AAPL)</p>
                          <p className="text-sm text-gray-500">Technology • $150.25</p>
                        </div>
                        <div className="p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
                          <p className="font-medium">Microsoft Corp. (MSFT)</p>
                          <p className="text-sm text-gray-500">Technology • $280.10</p>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Click outside handlers */}
      {(isUserMenuOpen || isNotificationsOpen) && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => {
            setIsUserMenuOpen(false);
            setIsNotificationsOpen(false);
          }}
        />
      )}
    </>
  );
}

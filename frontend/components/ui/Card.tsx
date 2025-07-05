import React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const cardVariants = cva(
  "rounded-lg border bg-card text-card-foreground transition-all",
  {
    variants: {
      variant: {
        default: "shadow-sm",
        elevated: "shadow-lg",
        outline: "border-2",
        ghost: "border-transparent bg-transparent",
        gradient: "bg-gradient-to-br from-card to-card/80 shadow-lg",
      },
      padding: {
        none: "p-0",
        sm: "p-4",
        default: "p-6",
        lg: "p-8",
      },
      hover: {
        none: "",
        lift: "hover:shadow-lg hover:-translate-y-1",
        glow: "hover:shadow-xl hover:shadow-primary/20",
        scale: "hover:scale-105",
      },
    },
    defaultVariants: {
      variant: "default",
      padding: "default",
      hover: "none",
    },
  }
)

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, padding, hover, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, padding, hover, className }))}
      {...props}
    />
  )
)
Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "text-2xl font-semibold leading-none tracking-tight",
      className
    )}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"

// Financial-specific card components
const MetricCard = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    title: string
    value: string | number
    change?: number
    icon?: React.ReactNode
    loading?: boolean
  }
>(({ className, title, value, change, icon, loading, ...props }, ref) => (
  <Card ref={ref} className={cn("relative overflow-hidden", className)} hover="lift" {...props}>
    <CardContent className="p-6">
      {loading ? (
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div className="h-8 bg-gray-200 rounded w-1/2"></div>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">{title}</p>
              <p className="text-3xl font-bold tracking-tight">{value}</p>
              {change !== undefined && (
                <p className={cn(
                  "text-sm font-medium",
                  change >= 0 ? "text-green-600" : "text-red-600"
                )}>
                  {change >= 0 ? "+" : ""}{change.toFixed(2)}%
                </p>
              )}
            </div>
            {icon && (
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                {icon}
              </div>
            )}
          </div>
        </>
      )}
    </CardContent>
  </Card>
))
MetricCard.displayName = "MetricCard"

const PerformanceCard = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    title: string
    value: string
    change: number
    timeframe: string
    chart?: React.ReactNode
  }
>(({ className, title, value, change, timeframe, chart, ...props }, ref) => (
  <Card ref={ref} className={cn("", className)} variant="elevated" {...props}>
    <CardHeader className="pb-3">
      <div className="flex items-center justify-between">
        <div>
          <CardTitle className="text-lg">{title}</CardTitle>
          <CardDescription>{timeframe}</CardDescription>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold">{value}</p>
          <p className={cn(
            "text-sm font-medium",
            change >= 0 ? "text-green-600" : "text-red-600"
          )}>
            {change >= 0 ? "+" : ""}{change.toFixed(2)}%
          </p>
        </div>
      </div>
    </CardHeader>
    {chart && (
      <CardContent className="pt-0">
        {chart}
      </CardContent>
    )}
  </Card>
))
PerformanceCard.displayName = "PerformanceCard"

const HoldingCard = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    symbol: string
    name: string
    quantity: number
    value: number
    change: number
    weight: number
  }
>(({ className, symbol, name, quantity, value, change, weight, ...props }, ref) => (
  <Card ref={ref} className={cn("", className)} hover="lift" {...props}>
    <CardContent className="p-4">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-xs font-bold text-primary">{symbol.slice(0, 2)}</span>
            </div>
            <div>
              <p className="font-semibold text-sm">{symbol}</p>
              <p className="text-xs text-muted-foreground truncate">{name}</p>
            </div>
          </div>
        </div>
        <div className="text-right">
          <p className="font-semibold">${value.toLocaleString()}</p>
          <p className={cn(
            "text-sm",
            change >= 0 ? "text-green-600" : "text-red-600"
          )}>
            {change >= 0 ? "+" : ""}{change.toFixed(2)}%
          </p>
          <p className="text-xs text-muted-foreground">{weight.toFixed(1)}% weight</p>
        </div>
      </div>
    </CardContent>
  </Card>
))
HoldingCard.displayName = "HoldingCard"

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
  MetricCard,
  PerformanceCard,
  HoldingCard,
} 
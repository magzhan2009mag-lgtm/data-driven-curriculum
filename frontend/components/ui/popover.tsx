"use client"

import { Popover as PopoverPrimitive } from "@base-ui/react/popover"
import { cn } from "@/lib/utils"

const Popover = PopoverPrimitive.Root
const PopoverTrigger = PopoverPrimitive.Trigger
const PopoverTitle = PopoverPrimitive.Title
const PopoverDescription = PopoverPrimitive.Description

function PopoverContent({
  className,
  children,
  side = "top",
  sideOffset = 6,
  ...props
}: PopoverPrimitive.Popup.Props & Pick<PopoverPrimitive.Positioner.Props, "side" | "sideOffset">) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Positioner side={side} sideOffset={sideOffset} className="z-50">
        <PopoverPrimitive.Popup
          data-slot="popover-content"
          className={cn(
            "w-72 max-w-[calc(100vw-2rem)] origin-(--transform-origin) rounded-md border bg-popover p-3 text-sm text-popover-foreground shadow-[0_6px_20px_-8px] shadow-foreground/25 transition-[scale,opacity] duration-150 ease-out outline-none data-ending-style:scale-[0.98] data-ending-style:opacity-0 data-starting-style:scale-[0.98] data-starting-style:opacity-0 motion-reduce:transition-none",
            className
          )}
          {...props}
        >
          {children}
        </PopoverPrimitive.Popup>
      </PopoverPrimitive.Positioner>
    </PopoverPrimitive.Portal>
  )
}

export { Popover, PopoverContent, PopoverDescription, PopoverTitle, PopoverTrigger }

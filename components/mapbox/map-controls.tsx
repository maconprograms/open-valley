"use client"
import { PlusIcon, MinusIcon, RotateCcw } from "lucide-react"
import { useMap } from "./map-context"
import { Button } from "../ui/button"

export default function MapControls() {
  const { map } = useMap()

  const zoomIn = () => {
    map?.zoomIn()
  }

  const zoomOut = () => {
    map?.zoomOut()
  }

  const resetView = () => {
    map?.flyTo({
      center: [-72.8648, 44.1159], // Warren, VT center
      zoom: 12,
      duration: 1000,
    })
  }

  return (
    <div className="absolute top-4 right-4 flex flex-col gap-2 z-10">
      <Button variant="outline" size="icon" onClick={zoomIn} className="bg-background/90 backdrop-blur-sm">
        <PlusIcon className="h-4 w-4" />
      </Button>
      <Button variant="outline" size="icon" onClick={zoomOut} className="bg-background/90 backdrop-blur-sm">
        <MinusIcon className="h-4 w-4" />
      </Button>
      <Button variant="outline" size="icon" onClick={resetView} className="bg-background/90 backdrop-blur-sm">
        <RotateCcw className="h-4 w-4" />
      </Button>
    </div>
  )
}

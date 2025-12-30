"use client";

interface PropertyData {
  span: string;
  address?: string;
  owner?: string;
  acres?: number;
  assessed_total?: number;
  property_type?: string;
  homestead?: boolean;
  lat?: number;
  lng?: number;
}

interface PropertyCardProps {
  data: unknown;
}

export default function PropertyCard({ data }: PropertyCardProps) {
  const property = data as PropertyData;

  if (!property?.span) {
    return (
      <div className="p-4 text-gray-400 text-center">
        No property data available
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4">
        <h3 className="text-lg font-semibold">
          {property.address || "No Address"}
        </h3>
        <p className="text-sm text-blue-100">SPAN: {property.span}</p>
      </div>

      {/* Body */}
      <div className="p-4 space-y-4">
        {/* Owner */}
        {property.owner && (
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">Owner</p>
            <p className="text-sm text-gray-900">{property.owner}</p>
          </div>
        )}

        {/* Value and Acres */}
        <div className="grid grid-cols-2 gap-4">
          {property.assessed_total !== undefined && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">
                Assessed Value
              </p>
              <p className="text-lg font-semibold text-gray-900">
                ${property.assessed_total.toLocaleString()}
              </p>
            </div>
          )}
          {property.acres !== undefined && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">
                Acreage
              </p>
              <p className="text-lg font-semibold text-gray-900">
                {property.acres.toFixed(2)} acres
              </p>
            </div>
          )}
        </div>

        {/* Type and Homestead */}
        <div className="flex gap-2 flex-wrap">
          {property.property_type && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              {property.property_type}
            </span>
          )}
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              property.homestead
                ? "bg-green-100 text-green-800"
                : "bg-orange-100 text-orange-800"
            }`}
          >
            {property.homestead ? "Primary Residence" : "Second Home / Other"}
          </span>
        </div>

        {/* Coordinates */}
        {property.lat && property.lng && (
          <div className="text-xs text-gray-400">
            📍 {property.lat.toFixed(4)}, {property.lng.toFixed(4)}
          </div>
        )}
      </div>
    </div>
  );
}

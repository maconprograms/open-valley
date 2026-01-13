"use client";

import { useState } from "react";

interface EntityCounts {
  parcels: number;
  dwellings: number;
  people: number;
  organizations: number;
  property_ownerships: number;
  str_listings: number;
  str_linked_dwellings: number;
}

interface DataModelDiagramProps {
  counts: EntityCounts;
}

type EntityKey =
  | "parcel"
  | "dwelling"
  | "person"
  | "organization"
  | "str"
  | "ownership";

interface EntityInfo {
  title: string;
  description: string;
  details: string[];
  color: string;
  bgColor: string;
  borderColor: string;
}

const entityDescriptions: Record<EntityKey, EntityInfo> = {
  parcel: {
    title: "Parcel",
    description:
      "A discrete piece of land identified by a unique SPAN (School Property Account Number).",
    details: [
      "Each parcel has a unique SPAN ID (e.g., 690-219-11993)",
      "Contains address, acreage, and assessed value",
      "One parcel can contain multiple dwellings (condos, multi-family)",
      "Source: Vermont Grand List",
    ],
    color: "text-blue-700",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
  },
  dwelling: {
    title: "Dwelling",
    description:
      "A habitable housing unit with sleeping, cooking, and sanitary facilities.",
    details: [
      "One parcel can have multiple dwellings (1:N relationship)",
      "Each dwelling has a DwellingUse: FULL_TIME_RESIDENCE, SECOND_HOME, or SHORT_TERM_RENTAL",
      "Dwellings can have STR listings attached as separate data",
      "Tax classification (HOMESTEAD, NHS_RESIDENTIAL) is derived from use",
    ],
    color: "text-emerald-700",
    bgColor: "bg-emerald-50",
    borderColor: "border-emerald-200",
  },
  person: {
    title: "Person",
    description: "An individual property owner parsed from Grand List records.",
    details: [
      "Parsed from owner names like 'PHILLIPS III ROBERT M & EMILY'",
      "Can own multiple properties through PropertyOwnership",
      "May be Warren resident (is_warren_resident flag)",
      "Linked to Front Porch Forum profiles if matched",
    ],
    color: "text-purple-700",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-200",
  },
  organization: {
    title: "Organization",
    description: "A legal entity that owns property: LLC, trust, or corporation.",
    details: [
      "Types: LLC, TRUST, CORPORATION, GOVERNMENT, NONPROFIT",
      "Extracted from owner names like 'MAD RIVER LLC'",
      "LLCs cannot file homestead declarations",
      "Trusts may link to a primary person (grantor/beneficiary)",
    ],
    color: "text-amber-700",
    bgColor: "bg-amber-50",
    borderColor: "border-amber-200",
  },
  str: {
    title: "STR Listing",
    description: "Short-term rental listings from Airbnb and VRBO.",
    details: [
      "STR listings are separate data, not a dwelling classification",
      "Any dwelling can have STR listings, even FULL_TIME_RESIDENCE",
      "A homeowner renting 2 weeks/year still has use=FULL_TIME_RESIDENCE",
      "Only 15 dwellings have validated STR links (name-matched to owners)",
    ],
    color: "text-rose-700",
    bgColor: "bg-rose-50",
    borderColor: "border-rose-200",
  },
  ownership: {
    title: "Property Ownership",
    description: "Links owners (people or organizations) to dwellings.",
    details: [
      "Many-to-many relationship between owners and dwellings",
      "Tracks ownership_share (e.g., 50% for joint ownership)",
      "Preserves original Grand List name (as_listed_name)",
      "Records acquired_date from property transfers",
    ],
    color: "text-slate-700",
    bgColor: "bg-slate-50",
    borderColor: "border-slate-200",
  },
};

function EntityNode({
  entityKey,
  count,
  label,
  isSelected,
  onClick,
}: {
  entityKey: EntityKey;
  count: number;
  label: string;
  isSelected: boolean;
  onClick: () => void;
}) {
  const info = entityDescriptions[entityKey];

  return (
    <button
      onClick={onClick}
      className={`
        relative px-4 py-3 rounded-lg border-2 transition-all duration-200
        ${isSelected ? `${info.bgColor} ${info.borderColor} ring-2 ring-offset-2 ring-${info.color.split("-")[1]}-400` : "bg-white border-gray-200 hover:border-gray-300"}
        ${isSelected ? "shadow-md" : "hover:shadow-sm"}
        cursor-pointer text-left w-full
      `}
    >
      <div className={`font-semibold ${isSelected ? info.color : "text-gray-900"}`}>
        {label}
      </div>
      <div className="text-2xl font-bold text-gray-900">
        {count.toLocaleString()}
      </div>
    </button>
  );
}

function RelationshipArrow({
  from,
  to,
  label,
}: {
  from: string;
  to: string;
  label: string;
}) {
  return (
    <div className="flex items-center justify-center text-gray-400 text-sm">
      <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">{label}</span>
    </div>
  );
}

export default function DataModelDiagram({ counts }: DataModelDiagramProps) {
  const [selectedEntity, setSelectedEntity] = useState<EntityKey | null>(null);

  const handleEntityClick = (entity: EntityKey) => {
    setSelectedEntity(selectedEntity === entity ? null : entity);
  };

  const selectedInfo = selectedEntity
    ? entityDescriptions[selectedEntity]
    : null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Data Model
      </h3>
      <p className="text-sm text-gray-600 mb-6">
        Click on any entity to learn more about what it represents and how it connects to other data.
      </p>

      {/* Diagram Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Row 1: Parcel */}
        <div className="md:col-start-2">
          <EntityNode
            entityKey="parcel"
            count={counts.parcels}
            label="Parcels"
            isSelected={selectedEntity === "parcel"}
            onClick={() => handleEntityClick("parcel")}
          />
        </div>

        {/* Arrow: Parcel -> Dwelling */}
        <div className="md:col-start-2 flex justify-center">
          <div className="flex flex-col items-center text-gray-400">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
            <span className="text-xs bg-gray-100 px-2 py-0.5 rounded mt-1">1:N</span>
          </div>
        </div>

        {/* Row 2: Dwelling + STR */}
        <div className="md:col-start-2">
          <EntityNode
            entityKey="dwelling"
            count={counts.dwellings}
            label="Dwellings"
            isSelected={selectedEntity === "dwelling"}
            onClick={() => handleEntityClick("dwelling")}
          />
        </div>

        {/* STR Listings - connected to Dwelling */}
        <div className="md:col-start-3 flex items-center gap-2">
          <div className="flex items-center text-gray-400">
            <svg className="w-4 h-4 rotate-90 md:rotate-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </div>
          <div className="flex-1">
            <EntityNode
              entityKey="str"
              count={counts.str_listings}
              label="STR Listings"
              isSelected={selectedEntity === "str"}
              onClick={() => handleEntityClick("str")}
            />
          </div>
        </div>

        {/* Arrow: Dwelling -> Ownership */}
        <div className="md:col-start-2 flex justify-center">
          <div className="flex flex-col items-center text-gray-400">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
            <span className="text-xs bg-gray-100 px-2 py-0.5 rounded mt-1">via</span>
          </div>
        </div>

        {/* Row 3: PropertyOwnership */}
        <div className="md:col-start-2">
          <EntityNode
            entityKey="ownership"
            count={counts.property_ownerships}
            label="Property Ownerships"
            isSelected={selectedEntity === "ownership"}
            onClick={() => handleEntityClick("ownership")}
          />
        </div>

        {/* Arrow: Ownership -> People/Orgs */}
        <div className="md:col-start-2 flex justify-center">
          <div className="flex flex-col items-center text-gray-400">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
            <span className="text-xs bg-gray-100 px-2 py-0.5 rounded mt-1">N:M</span>
          </div>
        </div>

        {/* Row 4: Person + Organization */}
        <div>
          <EntityNode
            entityKey="person"
            count={counts.people}
            label="People"
            isSelected={selectedEntity === "person"}
            onClick={() => handleEntityClick("person")}
          />
        </div>
        <div className="flex items-center justify-center text-gray-400 text-sm">
          or
        </div>
        <div>
          <EntityNode
            entityKey="organization"
            count={counts.organizations}
            label="Organizations"
            isSelected={selectedEntity === "organization"}
            onClick={() => handleEntityClick("organization")}
          />
        </div>
      </div>

      {/* Selected Entity Details */}
      {selectedInfo && (
        <div
          className={`rounded-lg border ${selectedInfo.borderColor} ${selectedInfo.bgColor} p-4 transition-all duration-200`}
        >
          <h4 className={`font-semibold ${selectedInfo.color} mb-2`}>
            {selectedInfo.title}
          </h4>
          <p className="text-gray-700 text-sm mb-3">{selectedInfo.description}</p>
          <ul className="text-sm text-gray-600 space-y-1">
            {selectedInfo.details.map((detail, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-gray-400 mt-1">•</span>
                <span>{detail}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Hint when nothing selected */}
      {!selectedInfo && (
        <div className="text-center text-sm text-gray-500 py-4 border border-dashed border-gray-200 rounded-lg">
          Click on any entity above to see details
        </div>
      )}
    </div>
  );
}

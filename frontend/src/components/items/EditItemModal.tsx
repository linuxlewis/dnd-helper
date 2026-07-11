import { useState } from 'react'
import { X } from 'lucide-react'
import { useUpdateItem } from '../../api/items'
import type { Item, ItemType, ItemRarity, ItemUpdate } from '../../api/types'
import { ITEM_TYPES, ITEM_RARITIES, TYPE_LABELS, RARITY_LABELS } from './utils'

interface EditItemModalProps {
  item: Item
  slug: string
  isOpen: boolean
  onClose: () => void
}

export function EditItemModal({ item, slug, isOpen, onClose }: EditItemModalProps) {
  // Use key on the form content to reset state when item changes
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4">
        {/* Backdrop */}
        <div className="fixed inset-0 bg-black/50" onClick={onClose} />

        {/* Modal - key prop ensures form resets when item changes */}
        <EditItemForm key={item.id} item={item} slug={slug} onClose={onClose} />
      </div>
    </div>
  )
}

interface EditItemFormProps {
  item: Item
  slug: string
  onClose: () => void
}

function EditItemForm({ item, slug, onClose }: EditItemFormProps) {
  const updateItem = useUpdateItem(slug, item.id)

  const [formError, setFormError] = useState<string | null>(null)
  const [name, setName] = useState(item.name)
  const [type, setType] = useState<ItemType>(item.type)
  const [category, setCategory] = useState(item.category)
  const [rarity, setRarity] = useState<ItemRarity>(item.rarity)
  const [description, setDescription] = useState(item.description || '')
  const [notes, setNotes] = useState(item.notes || '')
  const [quantityInput, setQuantityInput] = useState(String(item.quantity))
  const [weight, setWeight] = useState<number | ''>(item.weight ?? '')
  const [estimatedValue, setEstimatedValue] = useState<number | ''>(item.estimated_value ?? '')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!name.trim()) {
      setFormError('Name is required')
      return
    }

    const parsedQuantity = Number.parseInt(quantityInput, 10)
    const quantity = Number.isNaN(parsedQuantity) ? 1 : Math.max(1, parsedQuantity)

    const itemData: ItemUpdate = {
      name: name.trim(),
      type,
      category: category || type,
      rarity,
      description: description || undefined,
      notes: notes || undefined,
      quantity: quantity || 1,
      weight: weight || undefined,
      estimated_value: estimatedValue || undefined,
    }

    try {
      await updateItem.mutateAsync(itemData)
      onClose()
    } catch {
      setFormError('Failed to update item. Please try again.')
    }
  }

  return (
    <div className="relative w-full max-w-lg bg-gray-800 rounded-lg shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <h2 className="text-xl font-semibold text-gray-100">Edit Item</h2>
        <button
          onClick={onClose}
          className="p-1 text-gray-400 hover:text-gray-200 rounded-lg hover:bg-gray-700"
        >
          <X className="w-6 h-6" />
        </button>
      </div>

      {/* Body */}
      <form onSubmit={handleSubmit} className="p-4 space-y-4 max-h-[70vh] overflow-y-auto">
        {formError && (
          <div className="p-3 bg-red-900/30 border border-red-500 text-red-400 rounded">
            {formError}
          </div>
        )}

        {/* Name */}
        <div>
          <label htmlFor="edit-item-name" className="block text-sm font-medium text-gray-300 mb-1">
            Name <span className="text-red-500">*</span>
          </label>
          <input
            id="edit-item-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full px-3 py-2 bg-gray-700 text-gray-100 placeholder-gray-400 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-gray-800"
          />
        </div>

        {/* Type and Rarity */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="edit-item-type" className="block text-sm font-medium text-gray-300 mb-1">
              Type <span className="text-red-500">*</span>
            </label>
            <select
              id="edit-item-type"
              value={type}
              onChange={(e) => setType(e.target.value as ItemType)}
              className="w-full px-3 py-2 bg-gray-700 text-gray-100 placeholder-gray-400 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-gray-800"
            >
              {ITEM_TYPES.map((t) => (
                <option key={t} value={t}>
                  {TYPE_LABELS[t]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="edit-item-rarity" className="block text-sm font-medium text-gray-300 mb-1">
              Rarity
            </label>
            <select
              id="edit-item-rarity"
              value={rarity}
              onChange={(e) => setRarity(e.target.value as ItemRarity)}
              className="w-full px-3 py-2 bg-gray-700 text-gray-100 placeholder-gray-400 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-gray-800"
            >
              {ITEM_RARITIES.map((r) => (
                <option key={r} value={r}>
                  {RARITY_LABELS[r]}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Category */}
        <div>
          <label htmlFor="edit-item-category" className="block text-sm font-medium text-gray-300 mb-1">
            Category
          </label>
          <input
            id="edit-item-category"
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="e.g., Weapon, Armor, Adventuring Gear"
            className="w-full px-3 py-2 bg-gray-700 text-gray-100 placeholder-gray-400 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-gray-800"
          />
        </div>

        {/* Quantity and Weight */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="edit-item-quantity" className="block text-sm font-medium text-gray-300 mb-1">
              Quantity
            </label>
            <input
              id="edit-item-quantity"
              type="number"
              min="1"
              value={quantityInput}
              onChange={(e) => setQuantityInput(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 text-gray-100 placeholder-gray-400 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-gray-800"
            />
          </div>
          <div>
            <label htmlFor="edit-item-weight" className="block text-sm font-medium text-gray-300 mb-1">
              Weight (lbs)
            </label>
            <input
              id="edit-item-weight"
              type="number"
              min="0"
              step="0.1"
              value={weight}
              onChange={(e) => setWeight(e.target.value ? parseFloat(e.target.value) : '')}
              className="w-full px-3 py-2 bg-gray-700 text-gray-100 placeholder-gray-400 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-gray-800"
            />
          </div>
        </div>

        {/* Estimated Value */}
        <div>
          <label htmlFor="edit-item-value" className="block text-sm font-medium text-gray-300 mb-1">
            Estimated Value (GP)
          </label>
          <input
            id="edit-item-value"
            type="number"
            min="0"
            step="0.01"
            value={estimatedValue}
            onChange={(e) => setEstimatedValue(e.target.value ? parseFloat(e.target.value) : '')}
            className="w-full px-3 py-2 bg-gray-700 text-gray-100 placeholder-gray-400 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-gray-800"
          />
        </div>

        {/* Description */}
        <div>
          <label htmlFor="edit-item-description" className="block text-sm font-medium text-gray-300 mb-1">
            Description
          </label>
          <textarea
            id="edit-item-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 bg-gray-700 text-gray-100 placeholder-gray-400 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-gray-800 resize-none"
          />
        </div>

        {/* Notes */}
        <div>
          <label htmlFor="edit-item-notes" className="block text-sm font-medium text-gray-300 mb-1">
            Notes
          </label>
          <textarea
            id="edit-item-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="Personal notes about this item..."
            className="w-full px-3 py-2 bg-gray-700 text-gray-100 placeholder-gray-400 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-gray-800 resize-none"
          />
        </div>
      </form>

      {/* Footer */}
      <div className="flex justify-end gap-3 p-4 border-t border-gray-700 bg-gray-900 rounded-b-lg">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-gray-300 hover:bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 focus:ring-offset-gray-900 transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={updateItem.isPending}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 transition-colors"
        >
          {updateItem.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </div>
  )
}

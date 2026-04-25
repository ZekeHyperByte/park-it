/**
 * useCrud composable
 *
 * Reusable CRUD operations for any REST resource.
 * Built on top of useApi.
 *
 * @param {string} resourcePath — e.g. '/api/users'
 */

export const useCrud = (resourcePath) => {
  const { fetchApi } = useApi()

  if (!resourcePath) {
    throw new Error('useCrud requires a resourcePath')
  }

  // Ensure path starts with /
  const base = resourcePath.startsWith('/') ? resourcePath : `/${resourcePath}`

  async function list(params = {}) {
    const query = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        query.append(key, String(value))
      }
    }
    const qs = query.toString()
    return fetchApi(`${base}${qs ? '?' + qs : ''}`)
  }

  async function get(id) {
    return fetchApi(`${base}/${id}`)
  }

  async function create(payload) {
    return fetchApi(base, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async function update(id, payload) {
    return fetchApi(`${base}/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  }

  async function remove(id) {
    return fetchApi(`${base}/${id}`, {
      method: 'DELETE',
    })
  }

  return {
    list,
    get,
    create,
    update,
    remove,
  }
}

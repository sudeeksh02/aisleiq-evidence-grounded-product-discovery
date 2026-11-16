import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './ui';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const product = { product_id: 'p1', title: 'Evidence phone', category: 'mobile', price: 20000, rating: 4.2,
  reviews: [{ review_id: 'review-1', text: 'Battery life is great', rating: 5 }] };
const searchPayload = { intent: { raw_query: 'phone' }, retrieval_mode: 'bm25', count: 1, latency_ms: 4.2, notices: [],
  results: [{ product, score: .8, matched_attributes: ['battery'], supporting_reviews: product.reviews, pros: [], cons: [],
    explanation: ['Catalog title match'], confidence: .7, uncertainty: [] }] };

describe('AisleIQ discovery flow', () => {
  it('searches and opens product details with traceable review text', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/api/v1/search')) return Response.json(searchPayload);
      if (url.endsWith('/api/v1/products/p1')) return Response.json({ product, review_intelligence: {
        battery: { count: 1, sentiment: 'positive', evidence: product.reviews } } });
      throw new Error(`Unexpected URL ${url}`);
    }));
    render(<App />);
    fireEvent.change(screen.getByRole('textbox', { name: /describe what you are looking for/i }), { target: { value: 'phone' } });
    fireEvent.click(screen.getByRole('button', { name: /find my match/i }));
    expect(await screen.findByText('Evidence phone')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Evidence phone' }));
    expect(await screen.findByText('Catalog attributes')).toBeTruthy();
    await waitFor(() => expect(screen.getByText('Battery life is great')).toBeTruthy());
    expect(screen.getByText(/review-1/)).toBeTruthy();
  });

  it('shows a useful message when the API is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    render(<App />);
    fireEvent.change(screen.getByRole('textbox', { name: /describe what you are looking for/i }), { target: { value: 'phone' } });
    fireEvent.click(screen.getByRole('button', { name: /find my match/i }));
    expect(await screen.findByText('offline')).toBeTruthy();
  });

  it('compares three selected products and shows missing review information', async () => {
    const products = [product, { ...product, product_id: 'p2', title: 'Evidence phone 2' },
      { ...product, product_id: 'p3', title: 'Evidence phone 3' }];
    const many = { ...searchPayload, count: 3, results: products.map(p => ({ ...searchPayload.results[0], product: p })) };
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/api/v1/search')) return Response.json(many);
      if (url.endsWith('/api/v1/compare')) return Response.json({ products, attributes: { p1: {}, p2: {}, p3: {} }, missing_information: { p1: [], p2: [], p3: [] } });
      throw new Error(`Unexpected URL ${url}`);
    }));
    render(<App />);
    fireEvent.change(screen.getByRole('textbox', { name: /describe what you are looking for/i }), { target: { value: 'phone' } });
    fireEvent.click(screen.getByRole('button', { name: /find my match/i }));
    await screen.findByText('Evidence phone 3');
    for (const button of screen.getAllByLabelText('Add to compare')) fireEvent.click(button);
    fireEvent.click(screen.getByRole('button', { name: /compare 3/i }));
    expect(await screen.findByRole('heading', { name: /compare with clarity/i })).toBeTruthy();
    expect(screen.getByText('Evidence phone 2')).toBeTruthy();
  });
});

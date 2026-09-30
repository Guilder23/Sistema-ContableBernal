const moduleRoot = document.querySelector('.workspace--obligaciones');
const filterFrequency = moduleRoot?.querySelector('[data-filter-periodicity]');
const filterPeriod = moduleRoot?.querySelector('[data-filter-period-number]');
const generationFrequency = moduleRoot?.querySelector('[data-generation-frequency]');
const generationPeriod = moduleRoot?.querySelector('[data-generation-period]');
const generationYear = moduleRoot?.querySelector('[data-generation-year]');
const configurationForm = moduleRoot?.querySelector('.obligation-type-form');

const monthOptions = [
	['1', 'Enero'], ['2', 'Febrero'], ['3', 'Marzo'], ['4', 'Abril'],
	['5', 'Mayo'], ['6', 'Junio'], ['7', 'Julio'], ['8', 'Agosto'],
	['9', 'Septiembre'], ['10', 'Octubre'], ['11', 'Noviembre'], ['12', 'Diciembre'],
];
const quarterOptions = [
	['1', 'Primer trimestre'], ['2', 'Segundo trimestre'],
	['3', 'Tercer trimestre'], ['4', 'Cuarto trimestre'],
];

function populatePeriods(select, frequency, includeAll) {
	if (!select) return;
	select.replaceChildren();
	const options = includeAll ? [['', 'Todos']] : [];
	if (frequency === 'mensual') options.push(...monthOptions);
	if (frequency === 'trimestral') options.push(...quarterOptions);
	if (frequency === 'anual' && !includeAll) options.push(['0', 'Ejercicio fiscal']);

	options.forEach(([value, label]) => {
		const option = document.createElement('option');
		option.value = value;
		option.textContent = label;
		select.append(option);
	});
}

filterFrequency?.addEventListener('change', () => {
	populatePeriods(filterPeriod, filterFrequency.value, true);
});

function syncGenerationPeriod() {
	if (!configurationForm || !generationFrequency || !generationYear || !generationPeriod) return;
	configurationForm.querySelector('[data-config-generation="periodicidad"]').value = generationFrequency.value;
	configurationForm.querySelector('[data-config-generation="anio"]').value = generationYear.value;
	configurationForm.querySelector('[data-config-generation="periodo_numero"]').value = generationPeriod.value;
}

generationFrequency?.addEventListener('change', () => {
	populatePeriods(generationPeriod, generationFrequency.value, false);
	syncGenerationPeriod();
});
generationYear?.addEventListener('input', syncGenerationPeriod);
generationPeriod?.addEventListener('change', syncGenerationPeriod);

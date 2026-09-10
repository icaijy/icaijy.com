"""Original VCE-style banks calibrated against current VCAA study designs.

The questions deliberately use original wording.  Numerical variants are kept
short enough for a one-minute sprint and every distractor has concise feedback.
"""
from dataclasses import dataclass
from random import Random

from .question_bank import Question


@dataclass(frozen=True)
class Bank:
    id: str
    subject: str
    units: str
    technology: str
    reference_label: str
    reference_url: str
    accent: str
    questions: tuple[Question, ...]

    @property
    def title(self):
        tail = f' · {self.technology}' if self.technology else ''
        return f'{self.subject} · Units {self.units}{tail}'


def build_bank(bank_id, records):
    # A few TeX commands begin with characters Python also treats as string
    # escapes (for example \times and \frac). Restore those control characters
    # before the text reaches MathJax.
    def tex(value):
        if not isinstance(value, str):
            return value
        for control, escaped in (('\t', r'\t'), ('\b', r'\b'), ('\f', r'\f'), ('\v', r'\v'), ('\r', r'\r'), ('\a', r'\a')):
            value = value.replace(control, escaped)
        return value

    questions = []
    leads = (
        '{}',
        'A student is checking a worked solution. {}',
        'Which response best completes this VCE-style item? {}',
        'During a one-minute revision round: {}',
    )
    for number, record in enumerate(records):
        topic, prompt, correct, wrong, note = record
        for version, lead in enumerate(leads):
            pairs = [(correct, note)] + [(item, 'This does not satisfy the stated relationship.') for item in wrong]
            Random(f'{bank_id}-{number}-{version}').shuffle(pairs)
            questions.append(Question(
                id=f'{bank_id}-{number:02d}-{version}',
                prompt=tex(lead.format(prompt)),
                options=tuple(tex(item) for item, _ in pairs),
                answer_index=next(i for i, (item, _) in enumerate(pairs) if item == correct),
                explanations=tuple(tex(explanation) for _, explanation in pairs),
                source=f'Written for icaijy.com · {topic}',
                topic=topic,
            ))
    return tuple(questions)


CHEM_12 = [
    ('U1 · Atomic structure', 'An atom has 17 protons and 18 electrons. It is', r'\(\mathrm{Cl^-}\)', [r'\(\mathrm{Cl}\)', r'\(\mathrm{Cl^+}\)', r'\(\mathrm{Ar}\)'], 'One extra electron gives chlorine a −1 charge.'),
    ('U1 · Isotopes', 'Two isotopes of the same element must have the same number of', 'protons', ['neutrons', 'nucleons', 'electrons in every ion'], 'Atomic number, hence proton number, defines the element.'),
    ('U1 · Periodicity', 'Across Period 3 from left to right, atomic radius generally', 'decreases', ['increases', 'stays constant', 'first decreases then always doubles'], 'Increasing effective nuclear charge draws electrons closer.'),
    ('U1 · Periodicity', 'Down a group, first ionisation energy generally', 'decreases', ['increases', 'is exactly constant', 'becomes zero'], 'Outer electrons are further from the nucleus and more shielded.'),
    ('U1 · VSEPR', r'The molecular shape of ammonia, \(\mathrm{NH_3}\), is', 'pyramidal', ['linear', 'bent', 'tetrahedral'], 'Three bonding pairs and one lone pair give a pyramidal shape.'),
    ('U1 · Polarity', 'Carbon dioxide has polar bonds but is non-polar because', 'its linear bond dipoles cancel', ['C and O have equal electronegativity', 'it forms ionic bonds', 'it contains no valence electrons'], 'The molecule is linear and symmetric.'),
    ('U1 · Intermolecular forces', 'The strongest intermolecular attraction between water molecules is', 'hydrogen bonding', ['metallic bonding', 'ionic bonding', 'covalent network bonding'], 'O–H bonds allow hydrogen bonding between molecules.'),
    ('U1 · Structure and properties', 'Graphite conducts electricity mainly because it has', 'delocalised electrons within layers', ['mobile carbon ions', 'weak covalent bonds in each layer', 'free protons'], 'One electron per carbon is delocalised through each layer.'),
    ('U1 · Metals', 'Metals are malleable because', 'layers of positive ions can slide while metallic bonding persists', ['their molecules are soft', 'electrons are fixed between atom pairs', 'all metals have low melting points'], 'Non-directional attraction to delocalised electrons survives sliding.'),
    ('U1 · Ionic substances', 'Solid sodium chloride does not conduct electricity because', 'its ions cannot move through the lattice', ['it contains no charged particles', 'sodium is a non-metal', 'chloride ions lose their charge'], 'The charged ions are fixed in the solid lattice.'),
    ('U1 · Precipitation', r'Mixing \(\mathrm{AgNO_3(aq)}\) and \(\mathrm{NaCl(aq)}\) forms', r'\(\mathrm{AgCl(s)}\)', [r'\(\mathrm{NaNO_3(s)}\)', r'\(\mathrm{Cl_2(g)}\)', r'\(\mathrm{Ag(s)}\)'], 'Silver chloride is insoluble; sodium nitrate remains aqueous.'),
    ('U1 · Chromatography', r'A component travels 3.0 cm while the solvent front travels 5.0 cm. Its \(R_f\) is', '0.60', ['1.67', '2.0', '8.0'], r'\(R_f=3.0/5.0=0.60\).'),
    ('U1 · Chromatography', 'In a chromatogram, a pure substance under fixed conditions should ideally produce', 'one spot', ['four spots', 'no solvent front', 'a spot beyond the solvent front'], 'A single component ideally produces one spot.'),
    ('U1 · Sustainability', 'Reprocessing used aluminium into new aluminium products is closest to', 'a circular economy', ['a linear economy', 'complete biodegradation', 'carbon capture'], 'Material is recovered and returned to productive use.'),
    ('U1 · Formulae', 'The correct formula for aluminium sulfate is', r'\(\mathrm{Al_2(SO_4)_3}\)', [r'\(\mathrm{AlSO_4}\)', r'\(\mathrm{Al_3SO_4}\)', r'\(\mathrm{Al(SO_4)_2}\)'], 'Two Al³⁺ balance three sulfate ions.'),
    ('U1 · Equations', 'Which equation conserves atoms and charge?', r'\(\mathrm{Ag^+(aq)+Cl^-(aq)\rightarrow AgCl(s)}\)', [r'\(\mathrm{Ag^++2Cl^-\rightarrow AgCl}\)', r'\(\mathrm{Ag+Cl^-\rightarrow AgCl^-}\)', r'\(\mathrm{Ag^++Cl^-\rightarrow Ag+Cl}\)'], 'The net ionic equation is balanced for atoms and charge.'),
    ('U1 · Mole concept', 'How many moles are in 18.0 g of water?', '1.00 mol', ['0.500 mol', '18.0 mol', '324 mol'], r'\(n=m/M=18.0/18.0=1.00\).'),
    ('U1 · Avogadro constant', 'One mole of molecules contains approximately', r'\(6.02\times10^{23}\) molecules', [r'\(6.02\times10^{-23}\) molecules', '1 molecule', r'\(22.4\times10^3\) molecules'], 'One mole contains Avogadro’s number of entities.'),
    ('U1 · Empirical formula', 'A compound has 1 mol C atoms for every 2 mol H atoms. Its empirical formula is', r'\(\mathrm{CH_2}\)', [r'\(\mathrm{C_2H}\)', r'\(\mathrm{CH}\)', r'\(\mathrm{C_2H_4}\) only'], 'The simplest whole-number ratio is 1:2.'),
    ('U1 · Organic families', 'Which functional group identifies a carboxylic acid?', r'\(\mathrm{-COOH}\)', [r'\(\mathrm{-OH}\) only', r'\(\mathrm{C=C}\)', r'\(\mathrm{-Cl}\)'], 'Carboxylic acids contain the carboxyl group.'),
    ('U1 · Organic nomenclature', r'The IUPAC name of \(\mathrm{CH_3CH_2OH}\) is', 'ethanol', ['ethanal', 'ethene', 'methanol'], 'It is a two-carbon alcohol.'),
    ('U1 · Isomers', 'Structural isomers have', 'the same molecular formula but different connectivity', ['different molecular formulas only', 'identical structural formulas', 'the same physical properties in every case'], 'Structural isomers differ in how atoms are connected.'),
    ('U1 · Polymerisation', 'Polyethene is formed from ethene by', 'addition polymerisation', ['condensation polymerisation with water released', 'acid-base neutralisation', 'hydrolysis'], 'The C=C bonds open and monomers add without a small-molecule by-product.'),
    ('U1 · Polymers', 'A highly cross-linked polymer is usually', 'thermosetting', ['easily remelted as a thermoplastic', 'a monatomic gas', 'an ionic solution'], 'Cross-links prevent chains sliding when heated.'),
    ('U2 · Water', 'Ice is less dense than liquid water because its hydrogen-bonded structure is', 'more open', ['more tightly packed', 'ionic', 'free of intermolecular forces'], 'The solid lattice holds molecules further apart.'),
    ('U2 · Acids and bases', 'In the Brønsted–Lowry model, a base', 'accepts a proton', ['donates a proton', 'accepts an electron only', 'must contain hydroxide'], 'A Brønsted–Lowry base is a proton acceptor.'),
    ('U2 · Acids and bases', 'A strong acid differs from a weak acid because the strong acid', 'ionises to a greater extent in water', ['must be more concentrated', 'has a larger molar mass', 'contains more hydrogen atoms'], 'Strength describes extent of ionisation, not concentration.'),
    ('U2 · pH', r'The pH of \(1.0\times10^{-3}\ \mathrm{M\ HCl}\) is', '3.0', ['1.0', '7.0', '11.0'], r'For strong HCl, \([H^+]=10^{-3}\), so pH = 3.'),
    ('U2 · Redox', 'Oxidation is defined as', 'loss of electrons', ['gain of electrons', 'gain of protons only', 'formation of a precipitate'], 'Oxidation is electron loss.'),
    ('U2 · Gases', 'At SLC, the molar volume used in the VCAA data book is', r'\(24.8\ \mathrm{L\ mol^{-1}}\)', [r'\(22.4\ \mathrm{L\ mol^{-1}}\)', r'\(8.31\ \mathrm{L\ mol^{-1}}\)', r'\(100\ \mathrm{L\ mol^{-1}}\)'], 'At 25 °C and 100 kPa, the data-book value is 24.8 L mol⁻¹.'),
    ('U2 · Volumetric analysis', 'The most suitable apparatus for delivering one accurately known titration volume is a', 'burette', ['beaker', 'measuring cylinder', 'test tube'], 'A burette measures accurately the variable volume delivered.'),
    ('U2 · Calibration curves', 'An unknown absorbance lies beyond all standards on a calibration graph. The best action is to', 'dilute it into the calibrated range and account for dilution', ['extrapolate indefinitely', 'report zero concentration', 'change the wavelength after measuring'], 'Reliable interpolation requires the unknown to lie within the calibrated range.'),
]


CHEM_34 = [
    ('U3 · Energy', 'In a galvanic cell, oxidation occurs at the', 'anode', ['cathode', 'salt bridge', 'voltmeter'], 'Oxidation always occurs at the anode.'),
    ('U3 · Galvanic cells', 'The anode of a discharging galvanic cell is', 'negative', ['positive', 'uncharged by definition', 'alternating'], 'Electrons leave the negative anode.'),
    ('U3 · Galvanic cells', 'The salt bridge mainly', 'maintains electrical neutrality by ion migration', ['supplies electrons to the wire', 'raises activation energy', 'prevents all ion movement'], 'Ion migration completes the circuit and prevents charge build-up.'),
    ('U3 · Cell potentials', r'For standard half-cell potentials, \(E^\circ_{cell}\) is calculated as', r'\(E^\circ_{reduction}-E^\circ_{oxidation}\)', [r'\(E^\circ_{reduction}+E^\circ_{oxidation}\) using listed signs', r'\(IR\)', r'\(Q/t\)'], 'Subtract the listed reduction potential of the oxidation half-cell.'),
    ('U3 · Faraday laws', 'A current of 2.0 A flows for 30 s. The charge transferred is', '60 C', ['15 C', '32 C', '600 C'], r'\(Q=It=2.0\times30=60\ \mathrm C\).'),
    ('U3 · Fuel cells', 'A fuel cell differs from a battery because a fuel cell', 'requires a continuing external supply of reactants', ['cannot produce electricity', 'stores no chemical energy anywhere', 'must use a molten electrolyte'], 'Fuel and oxidant are continuously supplied.'),
    ('U3 · Biofuels', 'A major sustainability advantage of a biofuel can be', 'renewable feedstock', ['guaranteed zero emissions', 'infinite atom economy', 'no land use'], 'Biomass can be replenished, though impacts still require evaluation.'),
    ('U3 · Calorimetry', 'A calorimeter absorbs 8.0 kJ and rises by 4.0 °C. Its calibration factor is', r'\(2.0\ \mathrm{kJ\ ^\circ C^{-1}}\)', [r'\(0.50\ \mathrm{kJ\ ^\circ C^{-1}}\)', r'\(12\ \mathrm{kJ\ ^\circ C^{-1}}\)', r'\(32\ \mathrm{kJ\ ^\circ C^{-1}}\)'], r'\(CF=E/\Delta T=8.0/4.0=2.0\).'),
    ('U3 · Reaction rates', 'A catalyst increases reaction rate by', 'providing a pathway with lower activation energy', ['increasing reaction enthalpy', 'changing the equilibrium constant', 'being permanently consumed'], 'A catalyst lowers activation energy and is regenerated.'),
    ('U3 · Collision theory', 'Increasing temperature usually increases rate because particles', 'collide more often and a larger fraction exceed activation energy', ['become heavier', 'lower the activation energy themselves', 'stop colliding elastically'], 'Both collision frequency and the successful fraction increase.'),
    ('U3 · Equilibrium', 'At dynamic equilibrium in a closed system', 'forward and reverse reaction rates are equal', ['all concentrations are equal', 'reactions have stopped', 'all reactants are consumed'], 'Equal rates keep macroscopic concentrations constant.'),
    ('U3 · Le Chatelier', 'For an exothermic equilibrium, increasing temperature shifts equilibrium', 'towards reactants', ['towards products', 'nowhere under any conditions', 'until the catalyst is consumed'], 'Heat behaves as a product, so added heat favours the reverse reaction.'),
    ('U3 · Equilibrium constants', r'For a fixed balanced equation, \(K_c\) changes when', 'temperature changes', ['a catalyst is added', 'all concentrations are doubled instantly', 'surface area changes'], 'The equilibrium constant depends on temperature.'),
    ('U3 · Reaction quotient', r'If \(Q<K_c\), the net reaction proceeds', 'towards products', ['towards reactants', 'at equal forward and reverse rates immediately', 'only after adding catalyst'], 'More products form until Q reaches Kc.'),
    ('U3 · Electrolysis', 'In an electrolytic cell, the anode is connected to the', 'positive terminal', ['negative terminal', 'salt bridge only', 'neutral terminal'], 'The power supply removes electrons from the positive anode.'),
    ('U3 · Secondary cells', 'During recharge, a secondary cell operates as', 'an electrolytic cell', ['a spontaneous galvanic cell', 'a fuel cell', 'a calorimeter'], 'External electrical energy drives the reverse reaction.'),
    ('U4 · Organic reactions', 'An alkene reacting with bromine undergoes', 'addition', ['substitution', 'esterification', 'condensation polymer hydrolysis'], 'The C=C bond opens and bromine atoms add.'),
    ('U4 · Organic reactions', 'An alcohol and carboxylic acid can form an ester and', 'water', ['hydrogen', 'oxygen', 'ammonia'], 'Esterification is a condensation reaction producing water.'),
    ('U4 · Organic pathways', 'Oxidation of a primary alcohol can ultimately produce a', 'carboxylic acid', ['tertiary amine', 'haloalkane only', 'triglyceride directly'], 'A primary alcohol can oxidise via an aldehyde to a carboxylic acid.'),
    ('U4 · Green chemistry', 'Atom economy measures the proportion of reactant atoms incorporated into the', 'desired product', ['solvent', 'catalyst', 'waste only'], 'High atom economy places more reactant mass in the desired product.'),
    ('U4 · Mass spectrometry', 'The molecular ion peak is most directly used to estimate', 'molecular mass', ['boiling point', 'optical rotation', 'activation energy'], 'Its mass-to-charge ratio commonly gives the molecular mass.'),
    ('U4 · IR spectroscopy', 'A broad absorption associated with an alcohol most directly indicates an', 'O–H bond', ['C–Cl bond only', 'ionic lattice', 'unpaired neutron'], 'Alcohol O–H stretching produces a characteristic broad band.'),
    ('U4 · Carbon NMR', r'The number of signals in a low-resolution \(^{13}\mathrm C\)-NMR spectrum indicates the number of', 'distinct carbon environments', ['carbon atoms without regard to symmetry', 'hydrogen atoms', 'double bonds only'], 'Chemically equivalent carbon atoms share a signal.'),
    ('U4 · Proton NMR', 'A proton signal split into a triplet usually has how many equivalent neighbouring protons?', '2', ['0', '1', '3'], 'The n+1 rule gives n = 2.'),
    ('U4 · HPLC', 'Retention time is mainly used to', 'help identify a component under fixed conditions', ['measure nuclear charge', 'determine pH directly', 'balance redox equations'], 'Comparison with standards supports identification.'),
    ('U4 · Chirality', 'A tetrahedral carbon is chiral when bonded to', 'four different groups', ['four identical groups', 'two double bonds', 'one hydrogen only'], 'Four different substituents create a chiral centre.'),
    ('U4 · Enzymes', 'A competitive inhibitor reduces activity by', 'binding at the active site', ['breaking every peptide bond', 'raising substrate concentration to infinity', 'becoming the product'], 'It competes with substrate for the active site.'),
    ('U4 · Enzymes', 'High temperature may permanently reduce enzyme activity by', 'changing tertiary structure through denaturation', ['increasing primary sequence length', 'turning peptide bonds ionic', 'creating more active sites'], 'Disrupted interactions change the active-site shape.'),
    ('U4 · Distillation', 'Fractional distillation is preferred over simple distillation when liquids have', 'similar boiling points', ['very different colours', 'identical densities only', 'no intermolecular forces'], 'Repeated vaporisation-condensation improves separation of close boiling points.'),
    ('U4 · Experimental design', 'Repeating measurements primarily helps assess', 'random uncertainty and repeatability', ['the accepted value automatically', 'whether the hypothesis is true by definition', 'molar mass'], 'Repeated trials reveal spread and improve the estimate of random variation.'),
]


PHYS_12 = [
    ('U1 · Thermal physics', 'Temperature is most directly related to the particles’ average', 'translational kinetic energy', ['gravitational potential energy', 'rest mass', 'electric charge'], 'Temperature tracks average random translational kinetic energy.'),
    ('U1 · Thermal physics', 'During melting at constant pressure, added energy mainly', 'increases particle potential energy', ['increases temperature continuously', 'destroys energy', 'reduces internal energy'], 'Energy changes arrangement while temperature remains constant.'),
    ('U1 · Heat transfer', 'Convection transfers energy mainly through', 'bulk motion of a fluid', ['electromagnetic waves only', 'electron flow in a vacuum', 'nuclear decay'], 'Warmer fluid moves and carries internal energy.'),
    ('U1 · Radiation', 'An ideal black body is a perfect', 'absorber and emitter of radiation', ['mirror at every wavelength', 'thermal insulator', 'source of alpha particles'], 'A black body absorbs and emits electromagnetic radiation ideally.'),
    ('U1 · Nuclear physics', 'An alpha particle contains', 'two protons and two neutrons', ['one electron', 'one proton and one neutron', 'two photons'], 'It is a helium-4 nucleus.'),
    ('U1 · Nuclear physics', 'Beta-minus decay converts a neutron into', 'a proton, electron and antineutrino', ['two neutrons', 'an alpha particle', 'a photon only'], 'Charge and lepton number are conserved.'),
    ('U1 · Half-life', 'After three half-lives, the undecayed fraction is', r'\(1/8\)', [r'\(1/3\)', r'\(1/6\)', r'\(3/8\)'], r'\((1/2)^3=1/8\).'),
    ('U1 · Electricity', 'Conventional current in an external circuit is opposite to the drift of', 'electrons', ['positive ions in a metal lattice', 'photons', 'neutrons'], 'Electrons carry charge opposite to conventional-current direction.'),
    ('U1 · Circuits', 'Two resistors in series always carry the same', 'current', ['voltage', 'power', 'resistance'], 'There is one path for charge flow.'),
    ('U1 · Circuits', 'Two components connected in parallel have the same', 'potential difference', ['current in every branch', 'power', 'resistance'], 'Both ends connect to the same two nodes.'),
    ('U1 · Electrical energy', 'A 12 V device drawing 2.0 A uses power', '24 W', ['6 W', '10 W', '144 W'], r'\(P=VI=24\ \mathrm W\).'),
    ('U1 · Efficiency', 'A device receives 100 J and delivers 75 J usefully. Its efficiency is', '75%', ['25%', '100%', '133%'], 'Useful output divided by input is 0.75.'),
    ('U2 · Motion', 'The gradient of a displacement–time graph gives', 'velocity', ['acceleration', 'force', 'momentum'], 'Velocity is the rate of change of displacement.'),
    ('U2 · Motion', 'The area under a velocity–time graph gives', 'displacement', ['acceleration', 'force', 'power'], 'Integrating velocity over time gives displacement.'),
    ('U2 · Dynamics', 'For constant mass, the net force equals', r'\(m\vec a\)', [r'\(m/\vec a\)', r'\(\vec p/t^2\)', r'\(mv^2\) always'], 'Newton’s second law gives net force as mass times acceleration.'),
    ('U2 · Momentum', 'In an isolated collision, total', 'momentum is conserved', ['kinetic energy is always conserved', 'speed of each object is conserved', 'force is zero throughout'], 'Internal impulses cancel, conserving total momentum.'),
    ('U2 · Energy', 'Near Earth, gravitational potential energy change is', r'\(mg\Delta h\)', [r'\(mv\)', r'\(ma\Delta h\)', r'\(m/gh\)'], 'For a uniform field near Earth, ΔUg = mgΔh.'),
    ('U2 · Circular motion', 'For uniform circular motion, acceleration points', 'towards the centre', ['tangent to the circle', 'away from the centre', 'in the direction of velocity'], 'Centripetal acceleration changes the velocity direction inward.'),
    ('U2 · Waves', 'Wave frequency is determined by the', 'source', ['medium alone', 'amplitude', 'observer’s clock only'], 'The source sets the oscillation frequency.'),
    ('U2 · Waves', 'When a wave enters a new medium, its frequency usually', 'remains constant', ['becomes zero', 'must double', 'changes in inverse proportion to amplitude'], 'The boundary changes speed and wavelength, not source frequency.'),
    ('U2 · Sound', 'Increasing sound amplitude most directly increases', 'intensity', ['frequency', 'wave speed in the same medium', 'wavelength at fixed speed and frequency'], 'Greater amplitude carries more energy per area per time.'),
    ('U2 · Light', 'Refraction occurs because light', 'changes speed between media', ['changes frequency at the boundary', 'becomes charged', 'loses all energy'], 'A speed change produces a direction change except at normal incidence.'),
    ('U2 · Measurement', 'A result close to repeated measurements but far from the accepted value is', 'precise but inaccurate', ['accurate but imprecise', 'both accurate and precise', 'neither measurable nor valid'], 'Small spread means precision; bias from accepted value means inaccuracy.'),
    ('U2 · Experimental design', 'The independent variable is the quantity that is', 'deliberately changed', ['measured as the outcome', 'kept constant', 'ignored'], 'It is manipulated to test its effect.'),
]


PHYS_34 = [
    ('U3 · Newtonian motion', 'A passenger lurches forward when a car brakes because of', 'inertia', ['weight increasing', 'a forward engine force', 'loss of mass'], 'The passenger tends to maintain velocity unless acted on by a net force.'),
    ('U3 · Circular motion', 'The centripetal force on a satellite in circular orbit is supplied by', 'gravity', ['its engines continuously', 'air resistance', 'a magnetic force'], 'Gravity points towards the orbital centre.'),
    ('U3 · Gravitation', r'At distance \(r\) from a point mass, gravitational field strength varies as', r'\(1/r^2\)', [r'\(1/r\)', r'\(r\)', r'\(r^2\)'], 'The inverse-square law applies.'),
    ('U3 · Energy', 'For a projectile with negligible air resistance, total mechanical energy', 'remains constant', ['increases during descent', 'equals kinetic energy at all points', 'is zero at maximum height'], 'Gravity is conservative.'),
    ('U3 · Momentum', 'Impulse equals the change in', 'momentum', ['velocity only', 'kinetic energy', 'power'], r'\(J=\Delta p\).'),
    ('U3 · Collisions', 'A perfectly inelastic collision conserves', 'momentum but not kinetic energy', ['kinetic energy but not momentum', 'neither momentum nor energy', 'the speed of each object'], 'Objects stick; momentum is conserved in isolation but kinetic energy is transformed.'),
    ('U3 · Electric fields', 'The electric field direction is the direction of force on a', 'positive test charge', ['negative electron', 'neutron', 'magnetic north pole'], 'Field direction is defined using a positive test charge.'),
    ('U3 · Electric potential', 'Moving a positive charge against an electric field generally', 'increases electric potential energy', ['decreases its charge', 'removes its mass', 'leaves potential energy necessarily zero'], 'Work against the electric force stores potential energy.'),
    ('U3 · Magnetic forces', 'The magnetic force on a moving charge is zero when velocity is', 'parallel to the field', ['perpendicular to the field', 'at 45° only', 'opposite to its momentum'], r'\(F=qvB\sin\theta\), so parallel motion gives zero.'),
    ('U3 · Electromagnetic induction', 'Lenz’s law states that induced current acts to', 'oppose the change in magnetic flux', ['reinforce every flux change', 'remove resistance', 'make flux zero at all times'], 'The opposing response is consistent with energy conservation.'),
    ('U3 · Transformers', 'An ideal step-up transformer increases voltage and', 'decreases current', ['increases current', 'increases power', 'changes AC to DC'], 'Ideal input and output powers are equal.'),
    ('U3 · Power transmission', 'For fixed transmitted power, increasing voltage reduces line loss because current', 'decreases', ['increases', 'is unchanged', 'becomes alternating'], r'Loss \(P_{loss}=I^2R\), so lower current reduces heating.'),
    ('U3 · Relativity', 'According to special relativity, the speed of light in vacuum is', 'the same for all inertial observers', ['larger for observers moving toward the source', 'zero in the photon frame', 'dependent on source speed'], 'Invariant light speed is a postulate of special relativity.'),
    ('U3 · Relativity', 'A moving clock is observed from an inertial frame to run', 'slow', ['fast', 'backwards', 'at a rate set by its mass only'], 'Time dilation increases the observed interval between ticks.'),
    ('U3 · Relativity', 'Rest energy is given by', r'\(E_0=mc^2\)', [r'\(E_0=mv\)', r'\(E_0=mc\)', r'\(E_0=m/c^2\)'], 'Mass has rest-energy equivalent mc².'),
    ('U4 · Waves', 'Two coherent waves arrive in phase. They produce', 'constructive interference', ['destructive interference', 'polarisation only', 'photoelectric emission'], 'Their displacements reinforce.'),
    ('U4 · Diffraction', 'Diffraction is most significant when aperture width is', 'comparable to the wavelength', ['many orders larger than wavelength', 'exactly zero frequency', 'independent of wavelength'], 'Spreading becomes prominent at wavelength-scale openings.'),
    ('U4 · Standing waves', 'Adjacent nodes in a standing wave are separated by', r'\(\lambda/2\)', [r'\(\lambda\)', r'\(2\lambda\)', r'\(\lambda/4\)'], 'Nodes repeat every half-wavelength.'),
    ('U4 · Photoelectric effect', 'Below the threshold frequency, increasing light intensity causes', 'no photoelectron emission', ['higher maximum electron energy', 'emission after a fixed delay', 'the threshold frequency to decrease'], 'Individual photons still lack sufficient energy.'),
    ('U4 · Photoelectric effect', 'Above threshold, maximum photoelectron kinetic energy increases with', 'frequency', ['intensity only', 'surface area only', 'exposure time only'], r'\(K_{max}=hf-\phi\).'),
    ('U4 · Photons', 'The energy of one photon is', r'\(E=hf\)', [r'\(E=mv\)', r'\(E=h/f\)', r'\(E=qV^2\)'], 'Photon energy is proportional to frequency.'),
    ('U4 · Matter waves', 'The de Broglie wavelength of a particle is', r'\(\lambda=h/p\)', [r'\(\lambda=hp\)', r'\(\lambda=p/h\)', r'\(\lambda=hf\)'], 'Matter wavelength is inversely proportional to momentum.'),
    ('U4 · Atomic spectra', 'Discrete atomic emission lines provide evidence for', 'quantised energy levels', ['continuous electron energies only', 'absence of photons', 'classical planetary orbits alone'], 'Only particular photon-energy differences are emitted.'),
    ('U4 · Models of light', 'The double-slit interference pattern most directly demonstrates light’s', 'wave behaviour', ['electric charge', 'rest mass', 'sound speed'], 'Interference is characteristic of waves.'),
    ('U4 · Uncertainty', 'Reducing uncertainty in position generally causes uncertainty in momentum to', 'increase', ['decrease to zero', 'remain exactly fixed', 'become classical'], 'Position and momentum obey an inverse uncertainty relationship.'),
    ('U4 · Standard Model', 'A photon is the exchange particle for the', 'electromagnetic interaction', ['strong interaction', 'weak interaction', 'gravitational interaction in the Standard Model'], 'Photons mediate electromagnetic interactions.'),
    ('U4 · Data analysis', 'A straight-line graph with a non-zero intercept most clearly indicates', 'a possible systematic offset', ['zero uncertainty', 'proof of causation', 'random error only'], 'A persistent intercept may reveal calibration or background bias.'),
    ('U4 · Experimental design', 'Error bars that overlap substantially mean the measured values are', 'not clearly distinguishable within stated uncertainty', ['certainly identical', 'certainly different', 'invalid by definition'], 'The uncertainties do not support a clear difference.'),
]


METHODS_12_FREE = [
    ('U1–2 · Functions', r'The domain of \(f(x)=\sqrt{x-3}\) is', r'\([3,\infty)\)', [r'\((3,\infty)\)', r'\(({-\infty},3]\)', r'\(\mathbb R\)'], 'The radicand requires x−3 ≥ 0.'),
    ('U1–2 · Functions', r'For \(f(x)=2x-1\), \(f^{-1}(x)\) is', r'\((x+1)/2\)', [r'\(2x+1\)', r'\((x-1)/2\)', r'\(1/(2x-1)\)'], 'Swap x and y, then solve for y.'),
    ('U1–2 · Transformations', r'The graph of \(y=f(x-2)+3\) is translated', '2 right and 3 up', ['2 left and 3 up', '3 right and 2 down', '2 right and 3 down'], 'Horizontal translation uses the opposite sign inside.'),
    ('U1–2 · Quadratics', r'The vertex of \(y=(x-2)^2-5\) is', r'\((2,-5)\)', [r'\((-2,-5)\)', r'\((2,5)\)', r'\((-5,2)\)'], 'Vertex form y=(x−h)²+k has vertex (h,k).'),
    ('U1–2 · Polynomials', r'If \(P(3)=0\), then a factor of \(P(x)\) is', r'\(x-3\)', [r'\(x+3\)', r'\(3x-1\)', r'\(x^3\)'], 'The factor theorem gives x−3.'),
    ('U1–2 · Exponentials', r'For \(a>1\), \(y=a^x\) is', 'strictly increasing', ['strictly decreasing', 'periodic', 'undefined at x=0'], 'An exponential with base greater than one increases.'),
    ('U1–2 · Logarithms', r'\(\log_a(xy)\) equals', r'\(\log_a x+\log_a y\)', [r'\(\log_a x\log_a y\)', r'\(\log_a(x+y)\)', r'\(x+y\)'], 'The logarithm of a product is a sum.'),
    ('U1–2 · Trigonometry', r'The period of \(\sin(2x)\) is', r'\(\pi\)', [r'\(2\pi\)', r'\(\pi/2\)', r'\(4\pi\)'], 'Period is 2π/2 = π.'),
    ('U1–2 · Trigonometry', r'\(\sin^2x+\cos^2x\) equals', '1', ['0', r'\(\sin 2x\)', r'\(\tan x\)'], 'This is the Pythagorean identity.'),
    ('U1–2 · Algebra', r'The solution of \(|x|<3\) is', r'\((-3,3)\)', [r'\(({-\infty},-3)\cup(3,\infty)\)', r'\([-3,3]\)', r'\(x>3\)'], 'Distance from zero must be less than three.'),
    ('U1–2 · Rates of change', 'The average rate of change from x=a to x=b is', r'\(\frac{f(b)-f(a)}{b-a}\)', [r'\(f(b)-f(a)\)', r'\(\frac{b-a}{f(b)-f(a)}\)', r'\(f(a)+f(b)\)'], 'It is change in output divided by change in input.'),
    ('U1–2 · Differentiation', r'If \(f(x)=x^3\), then \(f\prime(x)=\)', r'\(3x^2\)', [r'\(x^2\)', r'\(3x\)', r'\(x^4/4\)'], 'Apply the power rule.'),
    ('U1–2 · Differentiation', 'At a stationary point of a differentiable function', r'\(f\prime(x)=0\)', [r'\(f(x)=0\)', r'\(f\prime\prime(x)=0\) always', r'\(f(x)=1\)'], 'The tangent gradient is zero.'),
    ('U1–2 · Probability', r'For events A and B, \(P(A\cup B)=\)', r'\(P(A)+P(B)-P(A\cap B)\)', [r'\(P(A)+P(B)\)', r'\(P(A)P(B)\)', r'\(1-P(A)\)'], 'Subtract the intersection counted twice.'),
    ('U1–2 · Probability', 'If A and B are independent, then', r'\(P(A\cap B)=P(A)P(B)\)', [r'\(P(A\cap B)=0\)', r'\(P(A)=P(B)\)', r'\(P(A\mid B)=0\)'], 'Independence gives the product rule.'),
    ('U1–2 · Probability', 'The expected value of a discrete random variable is', r'\(\sum xP(X=x)\)', [r'\(\sum P(X=x)\)', r'\(\max x\)', r'\(\sqrt{\mathrm{Var}(X)}\)'], 'Expectation is the probability-weighted mean.'),
]


METHODS_34_FREE = METHODS_12_FREE + [
    ('U3–4 · Chain rule', r'If \(y=(3x+1)^5\), then \(dy/dx=\)', r'\(15(3x+1)^4\)', [r'\(5(3x+1)^4\)', r'\(15(3x+1)^5\)', r'\((3x+1)^4\)'], 'Differentiate the outside and multiply by the inner derivative.'),
    ('U3–4 · Product rule', r'\(\frac d{dx}[xe^x]=\)', r'\(e^x(1+x)\)', [r'\(xe^x\)', r'\(e^x\)', r'\(x^2e^x\)'], 'Use uv′+u′v.'),
    ('U3–4 · Integration', r'\(\int 3x^2\,dx=\)', r'\(x^3+C\)', [r'\(6x+C\)', r'\(x^3\)', r'\(3x^3+C\)'], 'Reverse the power rule and include C.'),
    ('U3–4 · Fundamental theorem', r'\(\int_a^b f(x)\,dx\) represents', 'signed area between the graph and x-axis', ['total unsigned area always', 'the gradient at b', 'the mean of a and b'], 'A definite integral is signed area.'),
    ('U3–4 · Exponentials', r'A solution to \(dy/dt=ky\) has the form', r'\(y=Ae^{kt}\)', [r'\(y=Akt\)', r'\(y=A+k/t\)', r'\(y=A\sin kt\)'], 'A quantity with rate proportional to itself changes exponentially.'),
    ('U3–4 · Binomial distribution', r'For \(X\sim\mathrm{Bin}(n,p)\), \(E(X)=\)', r'\(np\)', [r'\(n+p\)', r'\(np(1-p)\)', r'\(p/n\)'], 'The binomial mean is np.'),
    ('U3–4 · Binomial distribution', r'For \(X\sim\mathrm{Bin}(n,p)\), \(\mathrm{Var}(X)=\)', r'\(np(1-p)\)', [r'\(np\)', r'\(n^2p\)', r'\(\sqrt{np(1-p)}\)'], 'The binomial variance is np(1−p).'),
    ('U3–4 · Normal distribution', 'A standard normal random variable has mean and variance', '0 and 1', ['1 and 0', '0 and 0', '1 and 1'], 'Standardisation produces mean 0 and variance 1.'),
    ('U3–4 · Confidence intervals', 'Increasing sample size while all else is fixed makes a confidence interval generally', 'narrower', ['wider', 'unchanged', 'centred at zero'], 'Standard error decreases as sample size grows.'),
    ('U3–4 · Conditional probability', r'\(P(A\mid B)=\)', r'\(\frac{P(A\cap B)}{P(B)}\)', [r'\(\frac{P(A)}{P(B)}\)', r'\(P(A\cup B)\)', r'\(P(A)P(B)\) always'], 'Restrict the sample space to B.'),
]


METHODS_12_ACTIVE = [
    ('U1–2 · CAS solving', r'A CAS solves \(x^3-4x=0\). The full solution set is', r'\(\{-2,0,2\}\)', [r'\(\{-2,2\}\)', r'\(\{0,4\}\)', r'\(\{-4,0,4\}\)'], 'Factor x(x−2)(x+2).'),
    ('U1–2 · Graphs', r'How many x-intercepts does \(y=x^4-5x^2+4\) have?', '4', ['0', '2', '5'], 'Let u=x²: (u−1)(u−4)=0 gives x=±1,±2.'),
    ('U1–2 · Intersections', r'The graphs \(y=x^2\) and \(y=2x+3\) intersect at x-values', r'\(x=-1,3\)', [r'\(x=1,3\)', r'\(x=-3,1\)', r'\(x=0,2\)'], 'Solve x²−2x−3=0.'),
    ('U1–2 · Exponentials', r'Solve \(2^x=10\), correct to two decimal places.', '3.32', ['2.30', '5.00', '10.00'], r'\(x=\log_2 10\approx3.32\).'),
    ('U1–2 · Trigonometry', r'On \([0,2\pi]\), \(\sin x=1/2\) at', r'\(\pi/6,5\pi/6\)', [r'\(\pi/3,2\pi/3\)', r'\(\pi/6,7\pi/6\)', r'\(5\pi/6,11\pi/6\)'], 'Sine is positive in quadrants I and II.'),
    ('U1–2 · Sequences', r'An arithmetic sequence has \(u_1=4\), common difference 3. Then \(u_{10}=\)', '31', ['27', '30', '34'], 'u10=4+9×3=31.'),
    ('U1–2 · Finance', '$1000 grows by 5% per year for 3 years. Its value is closest to', '$1157.63', ['$1050.00', '$1150.00', '$1250.00'], r'\(1000(1.05)^3=1157.625\).'),
    ('U1–2 · Numerical differentiation', r'For \(f(x)=x^2+1\), the tangent gradient at x=3 is', '6', ['3', '7', '10'], r'\(f\prime(x)=2x\).'),
    ('U1–2 · Probability simulation', 'A simulation estimates a probability as 0.37 from 10 000 trials. The expected count is', '3700', ['370', '9630', '10 000'], 'Expected count = trials × probability.'),
    ('U1–2 · Two-way tables', r'In a sample, 40 of 100 students play sport and 10 play sport and music. \(P(\text{music}\mid\text{sport})=\)', '0.25', ['0.10', '0.40', '0.50'], '10 of the 40 sport players also play music.'),
    ('U1–2 · Random variables', r'For X taking 0,1,2 with probabilities 0.2,0.5,0.3, \(E(X)=\)', '1.1', ['0.8', '1.0', '1.5'], '0×0.2+1×0.5+2×0.3=1.1.'),
    ('U1–2 · Modelling', 'A residual is defined as', 'observed value minus predicted value', ['predicted minus observed only', 'observed times predicted', 'gradient minus intercept'], 'Residual = y−ŷ.'),
    ('U1–2 · Regression', 'A correlation coefficient near −1 indicates', 'strong negative linear association', ['weak positive association', 'causation', 'a horizontal residual plot only'], 'Values near −1 show strong negative linear association.'),
    ('U1–2 · Domain restrictions', r'For \(f(x)=\log(x-4)\), the domain is', r'\((4,\infty)\)', [r'\([4,\infty)\)', r'\(({-\infty},4)\)', r'\(\mathbb R\)'], 'The logarithm argument must be positive.'),
    ('U1–2 · Composition', r'If \(f(x)=x+2\) and \(g(x)=x^2\), then \((g\circ f)(3)=\)', '25', ['11', '13', '7'], 'f(3)=5, then g(5)=25.'),
    ('U1–2 · Technology', 'A CAS returns a decimal root but the question requests an exact value. The best response is to', 'use an exact solve command or algebraic form', ['round to one decimal place', 'omit the root', 'change the equation'], 'Exact form is required when requested.'),
]


METHODS_34_ACTIVE = METHODS_12_ACTIVE + [
    ('U3–4 · Optimisation', r'The maximum of \(f(x)=-x^2+6x+1\) is', '10', ['1', '7', '19'], 'The vertex occurs at x=3, giving f(3)=10.'),
    ('U3–4 · Definite integrals', r'\(\int_0^2 (3x^2+1)\,dx=\)', '10', ['8', '9', '12'], r'\([x^3+x]_0^2=10\).'),
    ('U3–4 · Area', r'The area between \(y=x\) and the x-axis from 0 to 4 is', '8', ['4', '16', '32'], r'\(\int_0^4x\,dx=8\).'),
    ('U3–4 · Binomial probability', r'For \(X\sim\mathrm{Bin}(10,0.5)\), \(P(X=0)=\)', r'\(1/1024\)', [r'\(1/10\)', r'\(1/2\)', r'\(10/1024\)'], r'\((0.5)^{10}=1/1024\).'),
    ('U3–4 · Normal standardisation', 'For X with mean 50 and standard deviation 5, x=60 has z-score', '2', ['−2', '5', '12'], r'\(z=(60-50)/5=2\).'),
    ('U3–4 · Confidence intervals', 'A sample proportion is 0.40 and margin of error is 0.05. The interval is', r'\((0.35,0.45)\)', [r'\((0.40,0.45)\)', r'\((0.05,0.40)\)', r'\((0.30,0.50)\)'], 'Add and subtract the margin of error.'),
    ('U3–4 · Inverse functions', r'For \(f(x)=e^{2x}\), \(f^{-1}(x)=\)', r'\(\tfrac12\ln x\)', [r'\(2\ln x\)', r'\(e^{x/2}\)', r'\(\ln(2x)\)'], 'Take ln and divide by 2.'),
    ('U3–4 · Numerical modelling', 'A derivative changes from positive to negative at x=2. The function has a', 'local maximum at x=2', ['local minimum at x=2', 'vertical asymptote at x=2', 'point of inflection necessarily'], 'Increasing then decreasing gives a local maximum.'),
    ('U3–4 · Probability', r'If \(P(A)=0.6\), \(P(B)=0.5\), \(P(A\cap B)=0.3\), A and B are', 'independent', ['mutually exclusive', 'complements', 'impossible'], '0.6×0.5=0.3.'),
    ('U3–4 · Technology', 'A graphing window hides all turning points. The sound next step is to', 'determine a suitable domain/range analytically or with zoom', ['conclude none exist', 'delete the function', 'round all coefficients'], 'Window settings are not mathematical evidence.'),
]


SPEC_12_FREE = [
    ('U1–2 · Logic', 'The negation of “all integers are positive” is', 'at least one integer is not positive', ['all integers are not positive', 'at least one integer is positive', 'no integers exist'], 'Negating a universal statement produces an existential counterexample.'),
    ('U1–2 · Proof', 'A proof by contradiction begins by assuming', 'the negation of the desired conclusion', ['the conclusion itself', 'every lemma is false', 'a numerical example'], 'A contradiction disproves the negation.'),
    ('U1–2 · Number', r'If \(a\mid b\) and \(a\mid c\), then', r'\(a\mid(b+c)\)', [r'\(b\mid a\)', r'\(a=b+c\)', r'\(bc\mid a\)'], 'Divisibility is preserved under integer linear combinations.'),
    ('U1–2 · Sequences', r'A geometric sequence with ratio r has \(u_n=\)', r'\(u_1r^{n-1}\)', [r'\(u_1+(n-1)r\)', r'\(u_1r^n\)', r'\(nr\)'], 'There are n−1 ratio multiplications from the first term.'),
    ('U1–2 · Complex numbers', r'\(i^2=\)', '−1', ['1', 'i', '0'], 'This defines the imaginary unit.'),
    ('U1–2 · Complex numbers', r'The conjugate of \(3-2i\) is', r'\(3+2i\)', [r'\(-3+2i\)', r'\(2+3i\)', r'\(3-2i\)'], 'Change the sign of the imaginary part.'),
    ('U1–2 · Complex plane', r'The modulus of \(3+4i\) is', '5', ['7', '1', '25'], 'Use the Pythagorean theorem.'),
    ('U1–2 · Vectors', 'Two non-zero vectors are perpendicular when their dot product is', '0', ['1', '−1 always', 'their magnitude product'], 'The dot product includes cos 90° = 0.'),
    ('U1–2 · Vectors', 'The vector from A to B is', r'\(\vec b-\vec a\)', [r'\(\vec a-\vec b\)', r'\(\vec a+\vec b\)', r'\(\vec a\cdot\vec b\)'], 'Endpoint position minus start position.'),
    ('U1–2 · Matrices', r'The determinant of \(\begin{pmatrix}a&b\\c&d\end{pmatrix}\) is', r'\(ad-bc\)', [r'\(ac-bd\)', r'\(a+d\)', r'\(ab-cd\)'], 'Use ad−bc.'),
    ('U1–2 · Matrices', 'A square matrix is invertible exactly when its determinant is', 'non-zero', ['zero', 'one only', 'negative only'], 'A zero determinant means singular.'),
    ('U1–2 · Graph theory', 'The sum of degrees in an undirected graph equals', 'twice the number of edges', ['the number of vertices', 'the number of edges', 'twice the number of vertices'], 'Each edge contributes two degree incidences.'),
    ('U1–2 · Graph theory', 'A connected graph with n vertices and n−1 edges is a', 'tree', ['complete graph', 'multigraph necessarily', 'cycle'], 'This is a standard characterisation of a tree.'),
    ('U1–2 · Trigonometry', r'\(\cos(A-B)=\)', r'\(\cos A\cos B+\sin A\sin B\)', [r'\(\cos A\cos B-\sin A\sin B\)', r'\(\sin A\cos B\)', r'\(\cos A-\cos B\)'], 'Use the cosine difference identity.'),
    ('U1–2 · Geometry', 'The scalar projection of a onto non-zero b is', r'\(\frac{\vec a\cdot\vec b}{|\vec b|}\)', [r'\(\vec a\times\vec b\)', r'\(|\vec a||\vec b|\)', r'\(\frac{|\vec b|}{|\vec a|}\)'], 'Divide the dot product by the magnitude of b.'),
    ('U1–2 · Counting', 'The number of ways to choose r objects from n without order is', r'\(\binom nr\)', [r'\(n^r\)', r'\(n!\)', r'\(n-r\)'], 'Combinations ignore order.'),
]


SPEC_34_FREE = SPEC_12_FREE + [
    ('U3–4 · Complex roots', r'The roots of \(z^n=1\) are equally spaced on the', 'unit circle', ['real axis', 'imaginary axis', 'parabola'], 'Their moduli are one and arguments differ by 2π/n.'),
    ('U3–4 · Vectors', r'The cross product \(\vec a\times\vec b\) is', 'perpendicular to both vectors', ['parallel to both vectors', 'always zero', 'a scalar'], 'Its direction follows the right-hand rule.'),
    ('U3–4 · Vector lines', 'A vector equation of a line is', r'\(\vec r=\vec a+\lambda\vec d\)', [r'\(\vec r=\vec a\cdot\vec d\)', r'\(\vec r=\lambda\)', r'\(\vec r=\vec a\times\vec d\)'], 'A point plus a scalar multiple of a direction defines the line.'),
    ('U3–4 · Integration', r'\(\int e^{ax}\,dx=\)', r'\(\frac1a e^{ax}+C\)', [r'\(ae^{ax}+C\)', r'\(e^{ax}+C\)', r'\(\frac1x e^{ax}\)'], 'Differentiate to verify the factor 1/a.'),
    ('U3–4 · Differential equations', r'For \(dy/dx=f(x)g(y)\), separation gives', r'\(\frac{dy}{g(y)}=f(x)\,dx\)', [r'\(g(y)dy=f(x)dx\)', r'\(dy=f(x)+g(y)\)', r'\(dx/dy=f(x)g(y)\)'], 'Move the y factor with dy and x factor with dx.'),
    ('U3–4 · Kinematics', r'If position is \(\vec r(t)\), acceleration is', r'\(\vec r\prime\prime(t)\)', [r'\(\vec r\prime(t)\)', r'\(|\vec r(t)|\)', r'\(\int\vec r(t)dt\)'], 'Acceleration is the second time derivative of position.'),
    ('U3–4 · Mechanics', 'For a particle in equilibrium, the vector sum of forces is', r'\(\vec0\)', [r'\(m\vec v\)', r'\(m\vec g\) always', r'\(\vec r\)'], 'Zero net force is the equilibrium condition.'),
    ('U3–4 · Statistics', r'For independent random variables X and Y, \(\mathrm{Var}(X+Y)=\)', r'\(\mathrm{Var}(X)+\mathrm{Var}(Y)\)', [r'\(\mathrm{Var}(X)-\mathrm{Var}(Y)\)', r'\(\mathrm{Var}(X)\mathrm{Var}(Y)\)', r'\(0\)'], 'Covariance is zero under independence.'),
    ('U3–4 · Sample means', 'The standard deviation of the sample mean is', r'\(\sigma/\sqrt n\)', [r'\(\sigma/n\)', r'\(\sigma\sqrt n\)', r'\(n/\sigma\)'], 'This is the standard error of the mean.'),
    ('U3–4 · Hypothesis tests', 'A small p-value is evidence', 'against the null hypothesis', ['that the null is certainly true', 'that the alternative has probability p', 'of zero sampling variation'], 'It means the observed statistic is unusual under the null.'),
]


SPEC_12_ACTIVE = [
    ('U1–2 · Complex arithmetic', r'\((2+i)(3-i)=\)', r'\(7+i\)', [r'\(5-i\)', r'\(6-i\)', r'\(7-i\)'], 'Expand and use i²=−1.'),
    ('U1–2 · Polar form', r'The principal argument of \(-1+i\) is', r'\(3\pi/4\)', [r'\(\pi/4\)', r'\(-3\pi/4\)', r'\(5\pi/4\)'], 'The point lies in quadrant II.'),
    ('U1–2 · Matrices', r'The determinant of \(\begin{pmatrix}2&1\\3&4\end{pmatrix}\) is', '5', ['8', '11', '−5'], '2×4−1×3=5.'),
    ('U1–2 · Linear systems', r'The equations \(x+y=5\), \(x-y=1\) have solution', r'\((3,2)\)', [r'\((2,3)\)', r'\((4,1)\)', r'\((5,0)\)'], 'Add the equations to obtain x=3.'),
    ('U1–2 · Vectors', r'For \(\vec a=(1,2,2)\), \(|\vec a|=\)', '3', [r'\(\sqrt5\)', '5', '9'], r'\(\sqrt{1+4+4}=3\).'),
    ('U1–2 · Vectors', 'The angle between (1,0) and (1,1) is', r'\(\pi/4\)', [r'\(\pi/2\)', r'\(\pi\)', r'\(3\pi/4\)'], 'The dot-product cosine is 1/√2.'),
    ('U1–2 · Sequences', 'A geometric sequence has first term 3 and ratio 2. Its sixth term is', '96', ['48', '64', '192'], '3×2⁵=96.'),
    ('U1–2 · Series', r'\(1+2+4+8+16=\)', '31', ['30', '32', '64'], 'This finite geometric sum is 2⁵−1.'),
    ('U1–2 · Graphs', r'A complete graph \(K_6\) has how many edges?', '15', ['6', '12', '30'], r'\(6\times5/2=15\).'),
    ('U1–2 · Recurrence', r'If \(u_{n+1}=u_n+3\) and \(u_1=2\), then \(u_5=\)', '14', ['11', '15', '17'], 'Four increments of 3 give 14.'),
    ('U1–2 · Trigonometry', r'Solve \(2\cos x=1\) on \([0,2\pi]\).', r'\(x=\pi/3,5\pi/3\)', [r'\(x=\pi/6,5\pi/6\)', r'\(x=2\pi/3,4\pi/3\)', r'\(x=\pi/3,2\pi/3\)'], 'Cosine is 1/2 in quadrants I and IV.'),
    ('U1–2 · Counting', r'\(\binom{8}{2}=\)', '28', ['16', '56', '64'], '8×7/2=28.'),
    ('U1–2 · Numerical methods', r'One Newton step for \(f(x)=x^2-2\) from \(x_0=1.5\) gives', 'approximately 1.4167', ['approximately 1.2500', 'approximately 1.5000', 'approximately 2.0000'], r'\(x_1=x_0-f(x_0)/f\prime(x_0)\).'),
    ('U1–2 · Technology', 'A matrix inverse command fails because det(A)=0. This means A is', 'singular', ['orthogonal', 'the identity', 'diagonal with non-zero entries'], 'Zero determinant means no inverse.'),
    ('U1–2 · Modelling', 'A vector calculation returns magnitude −4. The correct interpretation is', 'a magnitude cannot be negative, so the setup or output is wrong', ['the vector points left', 'the vector points down', 'the magnitude is −4'], 'Magnitude is a non-negative scalar.'),
    ('U1–2 · Proof checking', 'Testing 10 000 cases with CAS establishes a universal integer claim', 'only if paired with a valid general proof', ['with certainty by itself', 'whenever no counterexample appears', 'only for prime inputs'], 'Finite checking alone does not prove an infinite claim.'),
]


SPEC_34_ACTIVE = SPEC_12_ACTIVE + [
    ('U3–4 · Complex equations', r'The solutions of \(z^2=-1\) are', r'\(z=\pm i\)', [r'\(z=\pm1\)', r'\(z=i\) only', r'\(z=0\)'], 'Both i and −i square to −1.'),
    ('U3–4 · Cross products', r'\((1,0,0)\times(0,1,0)=\)', r'\((0,0,1)\)', [r'\((0,0,-1)\)', r'\((1,1,0)\)', r'\(0\)'], 'The standard basis vectors satisfy i×j=k.'),
    ('U3–4 · Vector planes', r'The plane \(2x-y+2z=6\) has normal vector', r'\((2,-1,2)\)', [r'\((6,0,0)\)', r'\((2,1,2)\)', r'\((x,y,z)\)'], 'The coefficients form a normal vector.'),
    ('U3–4 · Arc length', r'The arc-length integrand for \(y=f(x)\) is', r'\(\sqrt{1+(f\prime(x))^2}\)', [r'\(1+f\prime(x)\)', r'\(\sqrt{f(x)}\)', r'\(f\prime\prime(x)\)'], 'Pythagoras on differential displacement gives the formula.'),
    ('U3–4 · Differential equations', r'Solve \(dy/dx=2y\), \(y(0)=3\).', r'\(y=3e^{2x}\)', [r'\(y=2e^{3x}\)', r'\(y=3+2x\)', r'\(y=3e^x\)'], 'Exponential growth rate is 2 with initial value 3.'),
    ('U3–4 · Kinematics', r'If \(v(t)=3t^2\) and \(s(0)=2\), then \(s(t)=\)', r'\(t^3+2\)', [r'\(6t+2\)', r'\(t^3\)', r'\(3t^3+2\)'], 'Integrate velocity and apply the initial position.'),
    ('U3–4 · Mechanics', 'A 2 kg particle has acceleration 3 m s⁻². Net force magnitude is', '6 N', ['1.5 N', '5 N', '9 N'], 'F=ma=6 N.'),
    ('U3–4 · Sample means', r'If \(\sigma=12\) and \(n=36\), the standard error is', '2', ['0.33', '6', '72'], r'\(12/\sqrt{36}=2\).'),
    ('U3–4 · Confidence intervals', 'An estimate 20 has margin of error 3. The interval is', r'\((17,23)\)', [r'\((20,23)\)', r'\((3,20)\)', r'\((14,26)\)'], 'Add and subtract the margin.'),
    ('U3–4 · Technology', 'A numerical solver reports one root. To check for omitted roots, first', 'inspect the domain and graph or use complete solve settings', ['assume uniqueness', 'round the root more', 'differentiate the answer'], 'Numerical solvers depend on domain, guesses and settings.'),
]


def make_subject_banks():
    chem_data = 'https://www.vcaa.vic.edu.au/sites/default/files/2026-02/2026-ChemistryDataBook_0.pdf'
    physics_sheet = 'https://www.vcaa.vic.edu.au/sites/default/files/2026-02/Physics-FormulaSheet.pdf'
    methods_1 = 'https://www.vcaa.vic.edu.au/sites/default/files/Documents/exams/mathematics/mathmethods1-formula-w.pdf'
    methods_2 = 'https://www.vcaa.vic.edu.au/sites/default/files/Documents/exams/mathematics/mathmethods2-formula-w.pdf'
    spec_1 = 'https://www.vcaa.vic.edu.au/sites/default/files/Documents/exams/mathematics/specmaths1-formula-w.pdf'
    spec_2 = 'https://www.vcaa.vic.edu.au/sites/default/files/Documents/exams/mathematics/specmaths2-formula-w.pdf'
    configs = (
        ('chemistry_u12', 'Chemistry', '1 & 2', '', CHEM_12, '2026 VCAA Chemistry Data Book', chem_data, '#ef4444'),
        ('chemistry_u34', 'Chemistry', '3 & 4', '', CHEM_12 + CHEM_34, '2026 VCAA Chemistry Data Book', chem_data, '#ef4444'),
        ('physics_u12', 'Physics', '1 & 2', '', PHYS_12, '2026 VCAA Physics Formula Sheet', physics_sheet, '#8b5cf6'),
        ('physics_u34', 'Physics', '3 & 4', '', PHYS_12 + PHYS_34, '2026 VCAA Physics Formula Sheet', physics_sheet, '#8b5cf6'),
        ('methods_u12_techfree', 'Mathematical Methods', '1 & 2', 'Tech-free', METHODS_12_FREE, 'VCAA Mathematical Methods Exam 1 Formula Sheet', methods_1, '#0ea5e9'),
        ('methods_u12_techactive', 'Mathematical Methods', '1 & 2', 'Tech-active', METHODS_12_ACTIVE, 'VCAA Mathematical Methods Exam 2 Formula Sheet', methods_2, '#0ea5e9'),
        ('methods_u34_techfree', 'Mathematical Methods', '3 & 4', 'Tech-free', METHODS_34_FREE, 'VCAA Mathematical Methods Exam 1 Formula Sheet', methods_1, '#0ea5e9'),
        ('methods_u34_techactive', 'Mathematical Methods', '3 & 4', 'Tech-active', METHODS_34_ACTIVE, 'VCAA Mathematical Methods Exam 2 Formula Sheet', methods_2, '#0ea5e9'),
        ('specialist_u12_techfree', 'Specialist Mathematics', '1 & 2', 'Tech-free', SPEC_12_FREE, 'VCAA Specialist Mathematics Exam 1 Formula Sheet', spec_1, '#f59e0b'),
        ('specialist_u12_techactive', 'Specialist Mathematics', '1 & 2', 'Tech-active', SPEC_12_ACTIVE, 'VCAA Specialist Mathematics Exam 2 Formula Sheet', spec_2, '#f59e0b'),
        ('specialist_u34_techfree', 'Specialist Mathematics', '3 & 4', 'Tech-free', SPEC_34_FREE, 'VCAA Specialist Mathematics Exam 1 Formula Sheet', spec_1, '#f59e0b'),
        ('specialist_u34_techactive', 'Specialist Mathematics', '3 & 4', 'Tech-active', SPEC_34_ACTIVE, 'VCAA Specialist Mathematics Exam 2 Formula Sheet', spec_2, '#f59e0b'),
    )
    return {bank_id: Bank(bank_id, subject, units, tech, label, url, accent, build_bank(bank_id, records)) for bank_id, subject, units, tech, records, label, url, accent in configs}

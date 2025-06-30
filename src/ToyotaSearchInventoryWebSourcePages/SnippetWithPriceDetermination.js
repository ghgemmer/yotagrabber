After javascript beautify of the following part taken from line 8 of C:\Users\GregG\Documents\GitHub\yotagrabber\src\ToyotaSearchInventoryWebSourcePages\166.626a79eb.chunk.js
const getPriceContent=function(e,i,t,n,o){if(e&&null!==i&&void 0!==i&&i.sellingPrice&&(null===i||void 0===i?void 0:i.sellingPrice)>=1e4)return{price:null===i||void 0===i?void 0:i.sellingPrice,label:getMSRPCopyString(t,!0,o),isDap:!0};const a=null!==n&&void 0!==n&&n.isSmartPath?null===i||void 0===i?void 0:i.advertizedPrice:null===i||void 0===i?void 0:i.nonSpAdvertizedPrice;return a&&a>=1e4?{price:a,label:getMSRPCopyString(t,!0,o),isDap:!(null!==n&&void 0!==n&&n.disableDAP)}:null!==i&&void 0!==i&&i.totalMsrp&&(null===i||void 0===i?void 0:i.totalMsrp)>=1e4?{price:null===i||void 0===i?void 0:i.totalMsrp,label:getMSRPCopyString(t,!0,o),isDap:!1}:{price:null===i||void 0===i?void 0:i.baseMsrp,label:getMSRPCopyString(t,!0,o),isDap:!1}}

we can summarize the selling price logic as
if Selling Price present and >= 10000 use selling price
elif isSmartPath is present and True and Advertised price present and  >= 10000 then use Advertised price
elif isSmartPath is (not (present and True)) and nonSpAdvertizedPrice price present and >= 10000 then use nonSpAdvertised price
elif TMSRP is present and >= 10000 use TMSRP and indicate Selling price incomplete.  (Note that I may change this to use TMSRP + DIO instead)
else use BMSRP and indicate Selling price incomplete.

const getPriceContent = function(e, i, t, n, o) {
        if (e && null !== i && void 0 !== i && i.sellingPrice && (null === i || void 0 === i ? void 0 : i.sellingPrice) >= 1e4) return {
            price: null === i || void 0 === i ? void 0 : i.sellingPrice,
            label: getMSRPCopyString(t, !0, o),
            isDap: !0
        };
        const a = null !== n && void 0 !== n && n.isSmartPath ? null === i || void 0 === i ? void 0 : i.advertizedPrice : null === i || void 0 === i ? void 0 : i.nonSpAdvertizedPrice;
        return a && a >= 1e4 ? {
            price: a,
            label: getMSRPCopyString(t, !0, o),
            isDap: !(null !== n && void 0 !== n && n.disableDAP)
        } : null !== i && void 0 !== i && i.totalMsrp && (null === i || void 0 === i ? void 0 : i.totalMsrp) >= 1e4 ? {
            price: null === i || void 0 === i ? void 0 : i.totalMsrp,
            label: getMSRPCopyString(t, !0, o),
            isDap: !1
        } : {
            price: null === i || void 0 === i ? void 0 : i.baseMsrp,
            label: getMSRPCopyString(t, !0, o),
            isDap: !1
        }
    },
    
function transformVLPData(e, i) {
var t;
if (!e) return [];
const n = null === i || void 0 === i || null === (t = i.brand) || void 0 === t ? void 0 : t.toLowerCase(),
    o = "toyota" === n ? D : C,
    a = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";
return e.map((function(e) {
    var t, r, l, d, s, c, p, u, g, h, x, m, y, v, b, f, A, w, j, k, C, D, $, T, M, S, I, N, z, L, P, E, B, F, O, V, H, R, U, G, Z, Q, Y, J, W, K, q;
    const X = {
            year: null === e || void 0 === e ? void 0 : e.year,
            marketingSeries: null === i || void 0 === i ? void 0 : i.seriesCode,
            distributorCd: null === e || void 0 === e ? void 0 : e.distributorCd
        },
        ee = {
            isSmartPath: null === e || void 0 === e ? void 0 : e.isSmartPath,
            dealerWebsite: null === e || void 0 === e ? void 0 : e.dealerWebsite,
            dealerCd: null === e || void 0 === e ? void 0 : e.dealerCd,
            vin: null === e || void 0 === e ? void 0 : e.vin,
            vdpUrl: null === e || void 0 === e ? void 0 : e.vdpUrl
        },
        ie = getPriceContent(!1, null === e || void 0 === e ? void 0 : e.price, {
            brand: null === e || void 0 === e ? void 0 : e.brand,
            dealerCd: null === e || void 0 === e ? void 0 : e.dealerCd,
            dealerMarketingName: null === e || void 0 === e ? void 0 : e.dealerMarketingName,
            dealerWebsite: null === e || void 0 === e ? void 0 : e.dealerWebsite
        }, {
            disableDAP: null === i || void 0 === i ? void 0 : i.disableDAP,
            isSmartPath: null === e || void 0 === e ? void 0 : e.isSmartPath
        }, null === i || void 0 === i ? void 0 : i.pricingData);
    if (null === ie.price) return;
    const te = !(null === i || void 0 === i || null === (t = i.dealerInfo) || void 0 === t || null === (r = t.preferredDealers) || void 0 === r || !r.find((function(i) {
            return (null === i || void 0 === i ? void 0 : i.dealerCd) === (null === e || void 0 === e ? void 0 : e.dealerCd)
        }))),
        ne = generateVdpUrl(n, ee);
    return {
        vin: null === e || void 0 === e ? void 0 : e.vin,
        marketingSeries: null === e || void 0 === e ? void 0 : e.marketingSeries,
        name: getName(null === e || void 0 === e ? void 0 : e.year, null === e || void 0 === e || null === (l = e.model) || void 0 === l ? void 0 : l.marketingName),
        trim: {
            value: `${null===e||void 0===e?void 0:e.year} ${null===e||void 0===e||null===(d=e.model)||void 0===d?void 0:d.marketingName}`.trim(),
            code: `${null===e||void 0===e||null===(s=e.model)||void 0===s?void 0:s.modelCd}-${null===e||void 0===e?void 0:e.year}`
        },
        stockNum: null === e || void 0 === e ? void 0 : e.stockNum,
        mileage: (null === e || void 0 === e ? void 0 : e.inventoryMileage) || 0,
        description: buildEngineString(n, e, X),
        isElectric: "E" === (null === e || void 0 === e || null === (c = e.engine) || void 0 === c ? void 0 : c.fuelType),
        isPreSold: null === e || void 0 === e ? void 0 : e.isPreSold,
        engine: {
            value: engineByBrand(null === e || void 0 === e || null === (p = e.engine) || void 0 === p ? void 0 : p.name, n, X),
            code: null === e || void 0 === e || null === (u = e.engine) || void 0 === u ? void 0 : u.engineCd
        },
        drivetrain: {
            value: drivetrainByBrand(null === e || void 0 === e || null === (g = e.drivetrain) || void 0 === g ? void 0 : g.title, n, X),
            code: null === e || void 0 === e || null === (h = e.drivetrain) || void 0 === h ? void 0 : h.code
        },
        baseMsrp: null === e || void 0 === e || null === (x = e.price) || void 0 === x ? void 0 : x.baseMsrp,
        msrp: null === ie || void 0 === ie ? void 0 : ie.price,
        msrpCopy: null === ie || void 0 === ie ? void 0 : ie.label,
        priceObject: ie,
        unlockPricingCTA: null !== e && void 0 !== e && e.isSmartPath && null !== e && void 0 !== e && e.isUnlockPriceDealer && (null === e || void 0 === e || null === (m = e.price) || void 0 === m || !m.sellingPrice) && null !== i && void 0 !== i && null !== (y = i.cmsData) && void 0 !== y && y.unlockPricingPath ? {
            text: null === i || void 0 === i || null === (v = i.cmsData) || void 0 === v ? void 0 : v.unlockPricingLabel,
            href: `${null===i||void 0===i||null===(b=i.cmsData)||void 0===b?void 0:b.unlockPricingPath}?source=t1&dealerCd=${null===e||void 0===e?void 0:e.dealerCd}&vin=${null===e||void 0===e?void 0:e.vin}&type=new&unlockSavings=true`,
            disableRouter: !0
        } : void 0,
        msrpLinks: createMsrpLinks(null === i || void 0 === i || null === (f = i.cmsData) || void 0 === f ? void 0 : f.msrpLinks, shouldShowPE(n, null === e || void 0 === e ? void 0 : e.distributorCd)),
        dealer: {
            value: getDealerLabel(null === e || void 0 === e ? void 0 : e.dealerMarketingName, null === e || void 0 === e ? void 0 : e.distance),
            code: null === e || void 0 === e ? void 0 : e.dealerCd,
            name: null === e || void 0 === e ? void 0 : e.dealerMarketingName,
            distance: null === e || void 0 === e ? void 0 : e.distance,
            isPMA: te,
            isSmartPath: null === e || void 0 === e ? void 0 : e.isSmartPath,
            dealerSiteURL: null === e || void 0 === e ? void 0 : e.dealerWebsite,
            status: transformDealerStatus(n, null === e || void 0 === e ? void 0 : e.isSmartPath, null === i || void 0 === i || null === (A = i.cmsData) || void 0 === A ? void 0 : A.smartPathDescription)
        },
        availability: [{
            name: "Show Sale Pending",
            value: "Sale Pending",
            code: "salePending",
            copy: `The sale on this ${null===i||void 0===i?void 0:i.brand} is pending and in the process of being finalized. We suggest contacting the dealer to confirm the latest status or to identify other vehicle options.`,
            valueToggle: null === e || void 0 === e ? void 0 : e.isPreSold
        }, {
            name: "Show In Transit",
            value: "In Transit",
            code: "inTransit",
            copy: `This ${null===i||void 0===i?void 0:i.brand} is still on its way to the designated dealer.`,
            valueToggle: "F" === (null === e || void 0 === e ? void 0 : e.dealerCategory) || "A" === (null === e || void 0 === e ? void 0 : e.dealerCategory)
        }],
        dealerCategory: null === e || void 0 === e ? void 0 : e.dealerCategory,
        category: null === e || void 0 === e ? void 0 : e.family,
        model: null === e || void 0 === e ? void 0 : e.marketingSeries,
        modelData: null === e || void 0 === e ? void 0 : e.model,
        year: `${null===e||void 0===e?void 0:e.year}`,
        extColor: {
            value: parseDD365Disclaimers(null === e || void 0 === e || null === (w = e.extColor) || void 0 === w ? void 0 : w.marketingName, n, X),
            label: parseDD365Disclaimers(null === e || void 0 === e || null === (j = e.extColor) || void 0 === j ? void 0 : j.marketingName, n, X),
            src: (null === e || void 0 === e || null === (k = e.extColor) || void 0 === k ? void 0 : k.colorSwatch) || "",
            hex: null === e || void 0 === e || null === (C = e.extColor) || void 0 === C ? void 0 : C.colorHexCd,
            code: null === e || void 0 === e || null === (D = e.extColor) || void 0 === D ? void 0 : D.colorCd,
            colorFamilies: null === e || void 0 === e || null === ($ = e.extColor) || void 0 === $ ? void 0 : $.colorFamilies
        },
        intColor: {
            value: parseDD365Disclaimers(null === e || void 0 === e || null === (T = e.intColor) || void 0 === T ? void 0 : T.marketingName, n, X),
            label: parseDD365Disclaimers(null === e || void 0 === e || null === (M = e.intColor) || void 0 === M ? void 0 : M.marketingName, n, X),
            code: null === e || void 0 === e || null === (S = e.intColor) || void 0 === S ? void 0 : S.colorCd,
            src: (null === e || void 0 === e || null === (I = e.intColor) || void 0 === I ? void 0 : I.colorSwatch) || "",
            colorFamilies: null === e || void 0 === e || null === (N = e.intColor) || void 0 === N ? void 0 : N.colorFamilies
        },
        inventoryStatus: null === e || void 0 === e ? void 0 : e.inventoryStatus,
        href: (null === e || void 0 === e ? void 0 : e.isSmartPath) && "toyota" === n && `${null===i||void 0===i||null===(z=i.cmsData)||void 0===z?void 0:z.unlockPricingPath}?source=t1&dealerCd=${null===e||void 0===e?void 0:e.dealerCd}&vin=${null===e||void 0===e?void 0:e.vin}&type=new`,
        interiorSwatch: {
            image: {
                desktop: {
                    src: (null === e || void 0 === e || null === (L = e.intColor) || void 0 === L ? void 0 : L.colorSwatch) || a,
                    alt: null === e || void 0 === e || null === (P = e.intColor) || void 0 === P ? void 0 : P.marketingName,
                    errorSrc: a
                }
            }
        },
        exteriorSwatch: {
            image: {
                desktop: {
                    src: (null === e || void 0 === e || null === (E = e.extColor) || void 0 === E ? void 0 : E.colorSwatch) || a,
                    alt: null === e || void 0 === e || null === (B = e.extColor) || void 0 === B ? void 0 : B.marketingName,
                    errorSrc: a
                }
            }
        },
        jelly: {
            image: {
                desktop: {
                    src: (null === e || void 0 === e || null === (F = e.jelly) || void 0 === F ? void 0 : F.href) || o,
                    alt: null === e || void 0 === e || null === (O = e.model) || void 0 === O ? void 0 : O.marketingName,
                    errorSrc: o
                }
            }
        },
        interiorJelly: {
            image: {
                desktop: {
                    src: (null === e || void 0 === e || null === (V = e.media) || void 0 === V || null === (H = V[1]) || void 0 === H ? void 0 : H.href) || o,
                    alt: null === e || void 0 === e || null === (R = e.model) || void 0 === R ? void 0 : R.marketingName,
                    errorSrc: o
                }
            }
        },
        price: null === ie || void 0 === ie ? void 0 : ie.price,
        priceData: null === e || void 0 === e ? void 0 : e.price,
        estMpg: `${null===e||void 0===e||null===(U=e.mpg)||void 0===U?void 0:U.city}/${null===e||void 0===e||null===(G=e.mpg)||void 0===G?void 0:G.highway} est. mpg`,
        options: getOptions(null === e || void 0 === e ? void 0 : e.options, n, X),
        cab: (null === e || void 0 === e || null === (Z = e.cab) || void 0 === Z ? void 0 : Z.title) || void 0,
        bed: (null === e || void 0 === e || null === (Q = e.bed) || void 0 === Q ? void 0 : Q.title) || void 0,
        series_number: null === e || void 0 === e || null === (Y = e.model) || void 0 === Y ? void 0 : Y.modelCd,
        vdpUrl: ne,
        dealerSiteURL: null === e || void 0 === e ? void 0 : e.dealerWebsite,
        isSmartPath: null === e || void 0 === e ? void 0 : e.isSmartPath,
        heartProperties: {
            type: "inv",
            brand: null === i || void 0 === i ? void 0 : i.brand,
            modelCd: null === e || void 0 === e || null === (J = e.model) || void 0 === J ? void 0 : J.modelCd,
            dealerCd: null === e || void 0 === e ? void 0 : e.dealerCd,
            advertisedPrice: null === e || void 0 === e || null === (W = e.price) || void 0 === W ? void 0 : W.advertizedPrice,
            imageHref: null === e || void 0 === e || null === (K = e.jelly) || void 0 === K ? void 0 : K.href,
            imagePrice: null === ie || void 0 === ie ? void 0 : ie.price,
            marketingSeries: null === e || void 0 === e ? void 0 : e.marketingSeries,
            marketingName: null === e || void 0 === e ? void 0 : e.marketingSeries,
            seriesGrade: getName(null === e || void 0 === e ? void 0 : e.year, null === e || void 0 === e || null === (q = e.model) || void 0 === q ? void 0 : q.marketingName),
            year: null === e || void 0 === e ? void 0 : e.year,
            vin: null === e || void 0 === e ? void 0 : e.vin,
            price: null === ie || void 0 === ie ? void 0 : ie.price,
            linkModule: null !== e && void 0 !== e && e.isSmartPath ? "mst" : null
        }
    }
}))

function useVehiclesByZipcode() {
    let {
        zip: e,
        model: i,
        brand: t = "Lexus",
        cmsData: o = {},
        loadMore: a = !1,
        distance: r = 50,
        lastDistance: d,
        keepPreviousData: s,
        disableDAP: c,
        pricingData: p = {},
        regions: u
    } = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : {};
    const g = (0, l.useRef)({});
    (!g.current[e] || Number.parseInt(g.current[e]) < Number.parseInt(r)) && (g.current[e] = r);
    const h = (0, n.jE)(),
        {
            client: x,
            leadId: m
        } = h.getDefaultOptions(),
        {
            data: y,
            error: v
        } = useDealerDataSystem({
            brand: t,
            zipCode: e,
            useDd365: !0
        });
    return dd365_useQuery([`vehicles-${e}-${i}-${g.current[e]}`], (async function() {
        var n;
        if (v) return Promise.reject({
            idError: "sit-server-error"
        });
        const {
            locateVehiclesByZip: a,
            error: l
        } = await getVehiclesByZip({
            generalClient: x,
            brand: t,
            zip: e,
            model: i,
            distance: g.current[e],
            leadId: m
        });
        if (l) return Promise.reject({
            idError: "sit-server-error"
        });
        if ((null === a || void 0 === a || null === (n = a.pagination) || void 0 === n ? void 0 : n.totalPages) > 1)
            for (let n = 2; n <= a.pagination.totalPages; n++) {
                const {
                    locateVehiclesByZip: o,
                    error: r
                } = await getVehiclesByZip({
                    generalClient: x,
                    brand: t,
                    zip: e,
                    model: i,
                    distance: g.current[e],
                    leadId: m,
                    page: n
                });
                if (r) return Promise.reject({
                    idError: "sit-server-error"
                });
                a.vehicleSummary.push(...o.vehicleSummary)
            }
        if (u.find((function(e) {
                return e.includes("sit-outside-region-" + (null === y || void 0 === y ? void 0 : y.state))
            }))) return Promise.reject({
            idError: "sit-outside-region-" + (null === y || void 0 === y ? void 0 : y.state)
        });
        const s = null !== a && void 0 !== a && a.vehicleSummary ? null === a || void 0 === a ? void 0 : a.vehicleSummary.length : 0;
        return r === d && 0 === s ? Promise.reject({
            idError: "sit-invalid-zip"
        }) : {
            vehicles: null !== a && void 0 !== a && a.vehicleSummary ? transformVLPData(a.vehicleSummary, {
                brand: t,
                cmsData: o,
                dealerInfo: y,
                disableDAP: c,
                seriesCode: i,
                pricingData: p
            }).filter((function(e) {
                var i;
                return void 0 !== e && (null === e || void 0 === e || null === (i = e.dealer) || void 0 === i ? void 0 : i.distance) <= r
            })) : [],
            dealerInfo: y
        }
    }), {
        keepPreviousData: s,
        enabled: Boolean(y)
    })
}


